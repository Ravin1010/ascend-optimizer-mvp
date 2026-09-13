"""Tests for Native 0G and Gimo live collectors."""

from pathlib import Path

import pandas as pd
import pytest

from src.ascend_optimizer.collect import append_snapshot_rows
from src.ascend_optimizer.collectors.gimo import (
    GimoNetworkObservation,
    GimoRateObservation,
    GimoRateSample,
    RPC_URL,
    ST0G_TOKEN_CONTRACT,
    annualize_exchange_rate_growth,
    append_rate_sample,
    build_gimo_observation,
    build_gimo_snapshot,
    fetch_current_gimo_rate_sample,
    fetch_gimo_network_observation,
    load_rate_history,
    select_reference_sample,
)
from src.ascend_optimizer.collectors.native_staking import (
    MIN_WITHDRAWABILITY_DELAY_SELECTOR,
    MODELLED_SEVERE_SLASH_STRESS,
    RPC_URL as NATIVE_RPC_URL,
    STAKING_CONTRACT,
    NativeNetworkObservation,
    ValidatorObservation,
    build_native_snapshot,
    fetch_0g_price_usd,
    fetch_withdrawal_delay_observation,
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
    ]

    row = build_native_snapshot(
        observations,
        timestamp="2026-09-13T00:00:00+00:00",
    )

    assert row["gross_apy"] == pytest.approx(0.15)
    assert row["bridge_fraction"] == 0
    assert row["data_status"] == "LIVE_INCOMPLETE"


def test_fetch_current_gimo_rate_uses_latest_state_only() -> None:
    def fake_rpc(url, method, params):
        assert url == RPC_URL

        if method == "eth_blockNumber":
            return hex(10)

        if method == "eth_getBlockByNumber":
            assert params == [hex(10), False]
            return {
                "number": hex(10),
                "timestamp": hex(1_000),
            }

        if method == "eth_call":
            assert params[0]["to"] == ST0G_TOKEN_CONTRACT
            assert params[1] == "latest"
            return hex(int(1.05 * 10**18))

        raise AssertionError(method)

    sample = fetch_current_gimo_rate_sample(rpc_fn=fake_rpc)

    assert sample.block_number == 10
    assert sample.block_timestamp == 1_000
    assert sample.rate == pytest.approx(1.05)


def test_annualize_exchange_rate_growth() -> None:
    result = annualize_exchange_rate_growth(
        current_rate=1.01,
        previous_rate=1.00,
        elapsed_seconds=365 * 86_400,
    )

    assert result == pytest.approx(0.01)


def test_first_gimo_sample_has_no_apy() -> None:
    current = GimoRateSample(
        rate=1.05,
        block_number=100,
        block_timestamp=2_000_000,
    )
    history = pd.DataFrame(
        columns=("timestamp", "block_number", "rate")
    )

    observation = build_gimo_observation(current, history)
    row = build_gimo_snapshot(
        observation,
        timestamp="2026-09-13T00:00:00+00:00",
    )

    assert observation.reference is None
    assert row["gross_apy"] is None
    assert row["yield_fee_status"] == "NET_OF_PROTOCOL_FEES"
    assert "no >=24h local getRate history yet" in row["notes"]


def test_reference_sample_requires_at_least_24h_history() -> None:
    current = GimoRateSample(
        rate=1.02,
        block_number=200,
        block_timestamp=1_000_000,
    )
    history = pd.DataFrame(
        [
            {
                "timestamp": 1_000_000 - 60 * 60,
                "block_number": 100,
                "rate": 1.01,
            }
        ]
    )

    assert select_reference_sample(history, current) is None


def test_reference_sample_prefers_seven_day_target() -> None:
    current = GimoRateSample(
        rate=1.02,
        block_number=500,
        block_timestamp=2_000_000,
    )
    history = pd.DataFrame(
        [
            {
                "timestamp": 2_000_000 - 2 * 86_400,
                "block_number": 200,
                "rate": 1.015,
            },
            {
                "timestamp": 2_000_000 - 7 * 86_400,
                "block_number": 100,
                "rate": 1.010,
            },
        ]
    )

    reference = select_reference_sample(history, current)

    assert reference is not None
    assert reference.block_number == 100
    assert reference.rate == pytest.approx(1.010)


def test_gimo_observation_derives_apy_from_local_history() -> None:
    current = GimoRateSample(
        rate=1.02,
        block_number=500,
        block_timestamp=2_000_000,
    )
    previous_ts = 2_000_000 - 7 * 86_400
    history = pd.DataFrame(
        [
            {
                "timestamp": previous_ts,
                "block_number": 100,
                "rate": 1.01,
            }
        ]
    )

    observation = build_gimo_observation(current, history)

    expected = annualize_exchange_rate_growth(
        1.02,
        1.01,
        7 * 86_400,
    )
    assert observation.realized_apy == pytest.approx(expected)
    assert observation.reference is not None


def test_append_rate_sample_preserves_history_and_deduplicates(
    tmp_path: Path,
) -> None:
    path = tmp_path / "gimo_rate_history.csv"

    first = GimoRateSample(
        rate=1.01,
        block_number=100,
        block_timestamp=1_000,
    )
    second = GimoRateSample(
        rate=1.02,
        block_number=200,
        block_timestamp=2_000,
    )

    append_rate_sample(first, path)
    append_rate_sample(first, path)
    append_rate_sample(second, path)

    history = load_rate_history(path)

    assert len(history) == 2
    assert list(history["block_number"]) == [100, 200]


def test_gimo_snapshot_with_history_is_net_of_protocol_fee() -> None:
    observation = GimoRateObservation(
        current=GimoRateSample(
            rate=1.02,
            block_number=200,
            block_timestamp=700_000,
        ),
        reference=GimoRateSample(
            rate=1.01,
            block_number=100,
            block_timestamp=95_200,
        ),
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
    assert row["source"] == "GIMO_ONCHAIN_GETRATE_LOCAL_HISTORY"


def test_append_snapshot_rows_preserves_history(tmp_path: Path) -> None:
    strategies = load_strategies(PROJECT_ROOT / "data" / "strategies.csv")
    output = tmp_path / "live.csv"

    first = pd.DataFrame(
        [{column: None for column in SNAPSHOT_COLUMNS}]
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


def test_native_snapshot_with_network_exposures_is_complete() -> None:
    observations = [
        ValidatorObservation(
            address="A",
            status="ACTIVE",
            total_delegations_0g=100,
            staking_apy=0.14,
            commission_rate=0.05,
            source_url="a",
        ),
        ValidatorObservation(
            address="B",
            status="ACTIVE",
            total_delegations_0g=300,
            staking_apy=0.16,
            commission_rate=0.05,
            source_url="b",
        ),
    ]
    network = NativeNetworkObservation(
        price_usd=2.0,
        withdrawal_delay_blocks=7200,
        average_block_seconds=1.0,
        exit_time_days=7200 / 86_400,
        slashing_stress_loss=MODELLED_SEVERE_SLASH_STRESS,
    )

    row = build_native_snapshot(
        observations,
        network=network,
        timestamp="2026-09-13T00:00:00+00:00",
    )

    assert row["liquidity_usd"] == pytest.approx(800.0)
    assert row["tvl_usd"] == pytest.approx(800.0)
    assert row["exit_time_days"] == pytest.approx(7200 / 86_400)
    assert row["slashing_stress_loss"] == pytest.approx(0.05)
    assert row["data_status"] == "PARTIAL_MODELLED"
    assert "MODELLED severe scenario" in row["notes"]


def test_fetch_native_price_from_geckoterminal() -> None:
    def fake_json(url, headers=None):
        return {
            "data": {
                "attributes": {
                    "token_prices": {
                        "0x1cd0690ff9a693f5ef2dd976660a8dafc81a109c": "1.75"
                    }
                }
            }
        }

    assert fetch_0g_price_usd(json_fn=fake_json) == pytest.approx(1.75)


def test_fetch_withdrawal_delay_observation_uses_staking_getter() -> None:
    calls = []

    def fake_rpc(url, method, params):
        calls.append((url, method, params))
        assert url == NATIVE_RPC_URL

        if method == "eth_call":
            assert params[0]["to"] == STAKING_CONTRACT
            assert params[0]["data"] == MIN_WITHDRAWABILITY_DELAY_SELECTOR
            assert params[1] == "latest"
            return hex(7200)

        if method == "eth_blockNumber":
            return hex(10_000)

        if method == "eth_getBlockByNumber":
            block_number = int(params[0], 16)
            if block_number == 10_000:
                return {"timestamp": hex(20_000)}
            if block_number == 9_000:
                return {"timestamp": hex(19_000)}

        raise AssertionError((method, params))

    delay_blocks, block_seconds, delay_days = (
        fetch_withdrawal_delay_observation(
            rpc_fn=fake_rpc,
            block_window=1000,
        )
    )

    assert delay_blocks == 7200
    assert block_seconds == pytest.approx(1.0)
    assert delay_days == pytest.approx(7200 / 86_400)


def test_fetch_gimo_network_observation_derives_tvl() -> None:
    def fake_rpc(url, method, params):
        assert url == RPC_URL
        assert method == "eth_call"
        selector = params[0]["data"]
        if selector == "0x18160ddd":
            return hex(2_000 * 10**18)
        if selector == "0x313ce567":
            return hex(18)
        raise AssertionError(selector)

    result = fetch_gimo_network_observation(
        1.05,
        rpc_fn=fake_rpc,
        price_fn=lambda: 2.0,
    )

    assert result.total_supply_st0g == pytest.approx(2000)
    assert result.tvl_0g == pytest.approx(2100)
    assert result.tvl_usd == pytest.approx(4200)
    assert result.slashing_stress_loss == pytest.approx(
        MODELLED_SEVERE_SLASH_STRESS
    )


def test_gimo_snapshot_with_network_exposure_is_partial_modelled() -> None:
    observation = GimoRateObservation(
        current=GimoRateSample(
            rate=1.02,
            block_number=200,
            block_timestamp=700_000,
        ),
        reference=None,
        realized_apy=None,
    )
    network = GimoNetworkObservation(
        total_supply_st0g=1000,
        tvl_0g=1020,
        price_usd=0.25,
        tvl_usd=255,
        slashing_stress_loss=0.05,
    )

    row = build_gimo_snapshot(
        observation,
        network=network,
        timestamp="2026-09-13T00:00:00+00:00",
    )

    assert row["gross_apy"] is None
    assert row["liquidity_usd"] == pytest.approx(255)
    assert row["tvl_usd"] == pytest.approx(255)
    assert row["slashing_stress_loss"] == pytest.approx(0.05)
    assert row["data_status"] == "PARTIAL_MODELLED"
    assert "underlying-validator severe scenario" in row["notes"]
