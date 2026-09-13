"""Tests for Native 0G and Gimo live collector parsing."""

from pathlib import Path

import pandas as pd
import pytest

import src.ascend_optimizer.collectors.gimo as gimo_module
from src.ascend_optimizer.collect import append_snapshot_rows
from src.ascend_optimizer.collectors.common import CollectionError
from src.ascend_optimizer.collectors.gimo import (
    GimoAppObservation,
    build_gimo_snapshot,
    fetch_gimo_observation,
    parse_gimo_app,
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


def test_parse_gimo_apr_from_raw_script_payload() -> None:
    html = """
    <html>
      <body><div>Loading Gimo Finance</div></body>
      <script>
        window.__APP_DATA__ = {
          "metric": "APR",
          "display": "6.84%"
        };
      </script>
    </html>
    """

    result = parse_gimo_app(html, retrieval_mode="raw-script")

    assert result.displayed_apr == pytest.approx(0.0684)
    assert result.retrieval_mode == "raw-script"


def test_gimo_fetch_retries_with_googlebot(monkeypatch) -> None:
    calls = []

    def fake_fetch(url, timeout=20, *, headers=None):
        calls.append(headers)
        if headers and "Googlebot" in headers.get("User-Agent", ""):
            return """
            APR 6.84%
            st0G Token Contract Address
            0x7bBC63D01CA42491c3E084C941c3E86e55951404
            st0G Stake Contract Address
            0xAc06d1Df23a4Fa00981aFAC0f33A5936Bd2135aF
            """
        return "Loading Gimo Finance"

    monkeypatch.setattr(gimo_module, "fetch_html", fake_fetch)

    result = fetch_gimo_observation()

    assert result.displayed_apr == pytest.approx(0.0684)
    assert result.retrieval_mode == "googlebot"
    assert len(calls) == 2


def test_gimo_fetch_reports_all_attempts(monkeypatch) -> None:
    monkeypatch.setattr(
        gimo_module,
        "fetch_html",
        lambda *args, **kwargs: "Loading Gimo Finance",
    )

    with pytest.raises(CollectionError, match="direct/googlebot/bingbot"):
        fetch_gimo_observation()


def test_gimo_snapshot_preserves_fee_ambiguity() -> None:
    observation = GimoAppObservation(
        displayed_apr=0.0684,
        st0g_token_contract="0x7bBC63D01CA42491c3E084C941c3E86e55951404",
        stake_contract="0xAc06d1Df23a4Fa00981aFAC0f33A5936Bd2135aF",
        retrieval_mode="googlebot",
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
    assert "retrieval_mode=googlebot" in row["notes"]


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
