"""Tests for Native 0G and Gimo live collector parsing."""

import pytest

from src.ascend_optimizer.collectors.gimo import (
    GimoAppObservation,
    build_gimo_snapshot,
    parse_gimo_app,
)
from src.ascend_optimizer.collectors.native_staking import (
    ValidatorObservation,
    build_native_snapshot,
    parse_validator_page,
)


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


def test_parse_gimo_app() -> None:
    text = """
    Stake 0G
    APR 6.84%
    st0G Token Contract Address
    0x7bBC63D01CA42491c3E084C941c3E86e55951404
    st0G Stake Contract Address
    0xAc06d1Df23a4Fa00981aFAC0f33A5936Bd2135aF
    """

    result = parse_gimo_app(text)

    assert result.displayed_apr == pytest.approx(0.0684)
    assert result.st0g_token_contract == (
        "0x7bBC63D01CA42491c3E084C941c3E86e55951404"
    )
    assert result.stake_contract == (
        "0xAc06d1Df23a4Fa00981aFAC0f33A5936Bd2135aF"
    )


def test_gimo_snapshot_preserves_fee_ambiguity() -> None:
    observation = GimoAppObservation(
        displayed_apr=0.0684,
        st0g_token_contract="0x7bBC63D01CA42491c3E084C941c3E86e55951404",
        stake_contract="0xAc06d1Df23a4Fa00981aFAC0f33A5936Bd2135aF",
    )

    row = build_gimo_snapshot(
        observation,
        timestamp="2026-09-13T00:00:00+00:00",
    )

    assert row["gross_apr"] == pytest.approx(0.0684)
    assert row["protocol_fee_rate"] == pytest.approx(0.10)
    assert row["yield_fee_status"] == "UNKNOWN"
    assert row["exit_time_days"] == pytest.approx(22)
    assert row["bridge_fraction"] == 0
    assert "fee basis unresolved" in row["notes"]
