"""Tests for Native 0G and Gimo live collectors."""

from pathlib import Path

import pandas as pd
import pytest

from src.ascend_optimizer.collect import append_snapshot_rows
from src.ascend_optimizer.collectors.gimo import (
    GimoRateObservation,
    RPC_URL,
    ST0G_TOKEN_CONTRACT,
    annualize_exchange_rate_growth,
    build_gimo_snapshot,
    fetch_gimo_rate_observation,
    find_block_at_or_before_timestamp,
)
from src.ascend_optimizer.collectors.native_staking import (
    ValidatorObservation,
    build_native_snapshot,
    parse_validator_page,
)
from src.ascend_optimizer.data_loader import (
    SNAPSHOT_COLUMNS,
    load_strategies,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_parse_native_validator_page() -> None:
    text = """
    Status ACTIVE
    Total Delegations 4,037,736 0G
    Staking APY 14.35%
    Commission 5.00%
    """

    result = parse_validator_page(
        text,
        address="0xabc",
        source_url="https://example.test",
    )

    assert result.status == "ACTIVE"
    assert result.total_delegations_0g == pytest.approx(4_037_736)
    assert result.staking_apy == pytest.approx(0.1435)
    assert result.commission_rate == pytest.approx(0.05)


def test_native_snapshot_is_delegation_weighted() -> None:
    observations = [
        ValidatorObservation(
            address="A",
            status="ACTIVE",
            total_delegations_0g=75,
            staking_apy=0.14,
            commission_rate=0.05,
            source_url="a",
        ),
        ValidatorObservation(
            address="B",
            status="ACTIVE",
            total_delegations_0g=25,
            staking_apy=0.18,
            commission_rate=0.10,
            source_url="b",
        ),
        ValidatorObservation(
            address="C",
            status="INACTIVE",
            total_delegations_0g=999,
            staking_apy=0.50,
            commission_rate=0.50,
            source_url="c",
        ),
    ]

    row = build_native_snapshot(
        observations,
        timestamp="2026-09-13T00:00:00+00:00",
    )

    assert row["gross_apy"] == pytest.approx(0.15)
    assert row["entry_slippage_rate"] == 0
    assert row["exit_slippage_rate"] == 0
    assert row["bridge_fraction"] == 0
    assert row["data_status"] == "LIVE_INCOMPLETE"
    assert "2 active sampled validators" in row["notes"]


def test_annualize_exchange_rate_growth() -> None:
    result = annualize_exchange_rate_growth(
        current_rate=1.01,
        previous_rate=1.00,
        elapsed_seconds=365 * 86_400,
    )

    assert result == pytest.approx(0.01)


def test_find_block_at_or_before_timestamp() -> None:
    def fake_rpc(url, method, params):
        assert url == RPC_URL
        assert method == "eth_getBlockByNumber"
        block_number = int(params[0], 16)
        return {
            "number": params[0],
            "timestamp": hex(block_number * 100),
        }

    block, timestamp = find_block_at_or_before_timestamp(
        750,
        latest_block=10,
        rpc_fn=fake_rpc,
    )

    assert block == 7
    assert timestamp == 700


def test_fetch_gimo_rate_observation_from_rpc() -> None:
    # Latest block 10 occurs at t=1000. A 300-second lookback selects block 7.
    # getRate rises from 1.000 to 1.001 over the 300-second observed interval.
    def fake_rpc(url, method, params):
        assert url == RPC_URL

        if method == "eth_blockNumber":
            return hex(10)

        if method == "eth_getBlockByNumber":
            block_number = int(params[0], 16)
            return {
                "number": params[0],
                "timestamp": hex(block_number * 100),
            }

        if method == "eth_call":
            assert params[0]["to"] == ST0G_TOKEN_CONTRACT
            block_number = int(params[1], 16)
            rate = 10**18 if block_number == 7 else int(1.001 * 10**18)
            return hex(rate)

        raise AssertionError(method)

    result = fetch_gimo_rate_observation(
        lookback_seconds=300,
        rpc_fn=fake_rpc,
    )

    expected_apy = (1.001 ** ((365 * 86_400) / 300)) - 1

    assert result.current_block == 10
    assert result.previous_block == 7
    assert result.current_rate == pytest.approx(1.001)
    assert result.previous_rate == pytest.approx(1.0)
    assert result.elapsed_seconds == 300
    assert result.realized_apy == pytest.approx(expected_apy)


def test_gimo_snapshot_is_net_of_protocol_fee() -> None:
    observation = GimoRateObservation(
        current_rate=1.02,
        previous_rate=1.01,
        current_block=200,
        previous_block=100,
        current_timestamp=700_000,
        previous_timestamp=95_200,
        elapsed_seconds=604_800,
        realized_apy=0.07,
    )

    row = build_gimo_snapshot(
        observation,
        timestamp="2026-09-13T00:00:00+00:00",
    )

    assert row["gross_apy"] == pytest.approx(0.07)
    assert row["protocol_fee_rate"] == pytest.approx(0.10)
    assert row["yield_fee_status"] == "NET_OF_PROTOCOL_FEES"
    assert row["exit_time_days"] == pytest.approx(22)
    assert row["bridge_fraction"] == 0
    assert row["source"] == "GIMO_ONCHAIN_GETRATE"
    assert "rate_now=" in row["notes"]


def test_append_snapshot_rows_preserves_history(tmp_path: Path) -> None:
    strategies = load_strategies(PROJECT_ROOT / "data" / "strategies.csv")
    output = tmp_path / "live.csv"

    first = pd.DataFrame(
        [
            {
                column: None
                for column in SNAPSHOT_COLUMNS
            }
        ]
    )
    first.loc[0, "timestamp"] = "2026-09-13T00:00:00+00:00"
    first.loc[0, "strategy_id"] = "NATIVE_STAKE_0G"
    first.loc[0, "gross_apy"] = 0.14
    first.loc[0, "yield_fee_status"] = "UNKNOWN"
    first.loc[0, "data_status"] = "LIVE_INCOMPLETE"
    first.loc[0, "source"] = "TEST"
    first.to_csv(output, index=False)

    second = first.copy()
    second.loc[0, "timestamp"] = "2026-09-13T01:00:00+00:00"
    second.loc[0, "gross_apy"] = 0.15

    combined, validated = append_snapshot_rows(
        output,
        second,
        strategies=strategies,
    )

    assert len(combined) == 2
    assert len(validated) == 2
    assert list(validated["gross_apy"]) == pytest.approx([0.14, 0.15])
