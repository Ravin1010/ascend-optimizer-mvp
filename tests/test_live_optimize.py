"""Tests for the personalized live optimizer helpers."""

from pathlib import Path
import json

import pytest

from src.ascend_optimizer.data_loader import load_snapshots, load_strategies
from src.ascend_optimizer.live_optimize import optimize_live, print_live_json


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _demo_inputs():
    strategies = load_strategies(PROJECT_ROOT / "data" / "strategies.csv")
    snapshots = load_snapshots(
        strategies,
        PROJECT_ROOT / "data" / "demo_strategy_snapshots.csv",
    )
    return strategies, snapshots


def test_live_optimizer_fetches_price_when_not_overridden() -> None:
    strategies, snapshots = _demo_inputs()
    calls = 0

    def fake_price():
        nonlocal calls
        calls += 1
        return 2.0

    run = optimize_live(
        strategies,
        snapshots,
        amount=1000,
        horizon_days=90,
        profile="Balanced",
        price_fn=fake_price,
    )

    assert calls == 1
    assert run.asset_price_usd == pytest.approx(2.0)
    assert run.portfolio_value_usd == pytest.approx(2000)
    assert run.profile == "Balanced"
    assert run.pipeline.result.deployed_weight == pytest.approx(1.0)


def test_live_optimizer_price_override_skips_price_fetch() -> None:
    strategies, snapshots = _demo_inputs()

    def should_not_run():
        raise AssertionError("price feed should not be called")

    run = optimize_live(
        strategies,
        snapshots,
        amount=500,
        horizon_days=30,
        profile="Aggressive",
        price_usd=1.25,
        price_fn=should_not_run,
    )

    assert run.asset_price_usd == pytest.approx(1.25)
    assert run.portfolio_value_usd == pytest.approx(625)


def test_live_optimizer_rejects_a0g_as_0g_alias() -> None:
    strategies, snapshots = _demo_inputs()

    with pytest.raises(ValueError, match="a0G is a separate live external"):
        optimize_live(
            strategies,
            snapshots,
            amount=100,
            horizon_days=90,
            profile="Balanced",
            asset="a0G",
            price_usd=1,
        )


def test_live_optimizer_annualizes_portfolio_horizon_return() -> None:
    strategies, snapshots = _demo_inputs()

    run = optimize_live(
        strategies,
        snapshots,
        amount=1000,
        horizon_days=90,
        profile="Conservative",
        price_usd=1,
    )

    expected = (
        (1 + run.pipeline.result.expected_net_return_horizon)
        ** (365 / 90)
        - 1
    )

    assert run.annualized_expected_net_apy == pytest.approx(expected)


def test_live_optimizer_exposes_profile_specific_status() -> None:
    strategies, snapshots = _demo_inputs()

    run = optimize_live(
        strategies,
        snapshots,
        amount=1000,
        horizon_days=90,
        profile="Balanced",
        price_usd=1,
    )

    assert "profile_eligible" in run.pipeline.candidates.columns
    assert "profile_exclusion_reasons" in run.pipeline.candidates.columns

    oku = run.pipeline.candidates.loc[
        run.pipeline.candidates["strategy_id"] == "OKU_LP_0G_USDC"
    ].iloc[0]

    assert not oku["profile_eligible"]
    assert "slippage_exceeds_profile_limit" in oku[
        "profile_exclusion_reasons"
    ]


def test_live_optimizer_keeps_live_ascend_gate_closed() -> None:
    strategies, snapshots = _demo_inputs()

    run = optimize_live(
        strategies,
        snapshots,
        amount=1000,
        horizon_days=90,
        profile="Balanced",
        price_usd=1,
    )

    ascend = run.pipeline.candidates.loc[
        run.pipeline.candidates["strategy_id"] == "ASCEND_STAKE_A0G"
    ].iloc[0]

    assert ascend["scope_eligible"]
    assert ascend["scope_exclusion_reason"] == ""
    assert not ascend["profile_eligible"]
    assert "allocation_gate=CLOSED" in (
        ascend["profile_exclusion_reasons"]
    )
    assert "ASCEND_STAKE_A0G" not in run.pipeline.result.allocations


def test_include_modelled_flag_does_not_override_closed_ascend_gate() -> None:
    strategies, snapshots = _demo_inputs()

    run = optimize_live(
        strategies,
        snapshots,
        amount=1000,
        horizon_days=90,
        profile="Balanced",
        price_usd=1,
        include_modelled=True,
    )

    ascend = run.pipeline.candidates.loc[
        run.pipeline.candidates["strategy_id"] == "ASCEND_STAKE_A0G"
    ].iloc[0]

    assert ascend["scope_eligible"]
    assert ascend["scope_exclusion_reason"] == ""
    assert not ascend["profile_eligible"]
    assert "allocation_gate=CLOSED" in (
        ascend["profile_exclusion_reasons"]
    )
    assert run.include_modelled



def test_live_optimizer_to_dict_is_frontend_ready_and_json_safe() -> None:
    strategies, snapshots = _demo_inputs()

    run = optimize_live(
        strategies,
        snapshots,
        amount=1000,
        horizon_days=90,
        profile="Balanced",
        price_usd=1,
    )

    payload = run.to_dict()

    assert payload["schema_version"] == "1.3"
    assert payload["input"]["asset"] == "0G"
    assert payload["input"]["profile"] == "Balanced"
    assert payload["input"]["portfolio_value_usd"] == pytest.approx(1000)

    portfolio = payload["portfolio"]
    assert portfolio["deployed_weight"] == pytest.approx(
        run.pipeline.result.deployed_weight
    )
    assert "bridge_exposure" in portfolio["stress"]
    assert "lp_il" in portfolio["stress"]
    assert "slashing" in portfolio["stress"]

    strategies_by_id = {
        row["strategy_id"]: row
        for row in payload["strategies"]
    }
    ascend = strategies_by_id["ASCEND_STAKE_A0G"]
    assert ascend["profile_eligible"] is False
    assert isinstance(ascend["exclusion_reasons"], list)

    # Strict JSON serialization must never rely on non-standard NaN tokens.
    encoded = json.dumps(payload, allow_nan=False)
    decoded = json.loads(encoded)
    assert decoded["schema_version"] == "1.3"


def test_live_optimizer_json_uses_null_for_missing_values() -> None:
    strategies, snapshots = _demo_inputs()

    run = optimize_live(
        strategies,
        snapshots,
        amount=1000,
        horizon_days=90,
        profile="Balanced",
        price_usd=1,
    )

    payload = run.to_dict()
    by_id = {
        row["strategy_id"]: row
        for row in payload["strategies"]
    }

    embedded = by_id["ASCEND_RESTAKE"]
    assert embedded["net_apy"] is None
    assert embedded["net_return_horizon"] is None
    assert embedded["return_error"] == (
        "embedded_exposure_no_independent_return"
    )


def test_print_live_json_emits_parseable_json(capsys) -> None:
    strategies, snapshots = _demo_inputs()

    run = optimize_live(
        strategies,
        snapshots,
        amount=250,
        horizon_days=30,
        profile="Aggressive",
        price_usd=2,
    )

    print_live_json(run)
    output = capsys.readouterr().out

    payload = json.loads(output)
    assert payload["input"]["amount"] == pytest.approx(250)
    assert payload["input"]["asset_price_usd"] == pytest.approx(2)
    assert payload["input"]["profile"] == "Aggressive"



def test_json_exposes_profile_constraints_and_binding_limits() -> None:
    strategies, snapshots = _demo_inputs()

    run = optimize_live(
        strategies,
        snapshots,
        amount=1000,
        horizon_days=90,
        profile="Balanced",
        price_usd=1,
    )

    payload = run.to_dict()
    limits = payload["profile_constraints"]

    assert limits["max_strategy_concentration"] == pytest.approx(0.60)
    assert limits["max_entry_exit_slippage"] == pytest.approx(0.01)
    assert limits["max_exit_time_days"] == pytest.approx(30.0)
    assert "max_strategy_concentration" in limits["at_limit_constraints"]

    observed = limits["observed"]
    assert observed["max_allocated_strategy_weight"] == pytest.approx(0.60)


def test_json_marks_profile_constraints_triggered_by_excluded_routes() -> None:
    strategies, snapshots = _demo_inputs()

    run = optimize_live(
        strategies,
        snapshots,
        amount=1000,
        horizon_days=90,
        profile="Balanced",
        price_usd=1,
    )

    payload = run.to_dict()

    assert "max_entry_exit_slippage" in (
        payload["profile_constraints"]["triggered_constraints"]
    )



def test_json_exposes_per_strategy_constraint_headroom() -> None:
    strategies, snapshots = _demo_inputs()

    run = optimize_live(
        strategies,
        snapshots,
        amount=1000,
        horizon_days=90,
        profile="Balanced",
        price_usd=1,
    )

    payload = run.to_dict()
    by_id = {
        row["strategy_id"]: row
        for row in payload["strategies"]
    }

    native = by_id["NATIVE_STAKE_0G"]
    native_concentration = native["constraint_diagnostics"][
        "strategy_concentration"
    ]

    assert native_concentration["value"] == pytest.approx(0)
    assert native_concentration["limit"] == pytest.approx(0.60)
    assert native_concentration["headroom"] == pytest.approx(0.60)
    assert native_concentration["state"] == "WITHIN_LIMIT"

    gimo = by_id["GIMO_STAKE_0G"]
    gimo_concentration = gimo["constraint_diagnostics"][
        "strategy_concentration"
    ]

    assert gimo_concentration["value"] == pytest.approx(0.40)
    assert gimo_concentration["limit"] == pytest.approx(0.60)
    assert gimo_concentration["headroom"] == pytest.approx(0.20)
    assert gimo_concentration["state"] == "WITHIN_LIMIT"

    jaine = by_id["JAINE_LP_0G_USDC"]["constraint_diagnostics"]["strategy_concentration"]
    assert jaine["value"] == pytest.approx(0.60)
    assert jaine["headroom"] == pytest.approx(0)
    assert jaine["state"] == "AT_LIMIT"

    oku = by_id["OKU_LP_0G_USDC"]
    slippage = oku["constraint_diagnostics"]["slippage"]

    assert slippage["limit"] == pytest.approx(0.01)
    assert slippage["value"] is not None
    assert slippage["headroom"] == pytest.approx(
        0.01 - slippage["value"]
    )
    assert slippage["state"] in {"NEAR_LIMIT", "EXCEEDED"}


def test_legacy_modelled_status_cannot_remove_canonical_jaine_or_open_ascend() -> None:
    strategies, snapshots = _demo_inputs()
    strategies.loc[strategies.strategy_id.eq("JAINE_LP_0G_USDC"), "execution_status"] = "MODELLED"
    strategies.loc[strategies.strategy_id.eq("JAINE_LP_0G_USDC"), "technical_eligibility"] = "EXCLUDED_LIQUIDITY_CONSTRAINED"
    strategies.loc[strategies.strategy_id.eq("ASCEND_STAKE_A0G"), "technical_eligibility"] = "ELIGIBLE"
    run = optimize_live(strategies, snapshots, amount=1000, price_usd=1,
                        horizon_days=90, profile="Balanced", include_modelled=False)
    assert run.pipeline.result.allocations["JAINE_LP_0G_USDC"] == pytest.approx(0.60)
    assert "ASCEND_STAKE_A0G" not in run.pipeline.result.allocations
    assert run.to_dict()["schema_version"] == "1.3"


def test_compatibility_flag_preserves_scope_and_terminal_wording(capsys) -> None:
    from src.ascend_optimizer.data_loader import MVP_STRATEGY_IDS
    from src.ascend_optimizer.live_optimize import print_live_run

    strategies, snapshots = _demo_inputs()
    allocations = []
    scope_lines = []
    for flag in (False, True):
        run = optimize_live(strategies, snapshots, amount=1000, price_usd=1,
                            horizon_days=90, profile="Balanced", include_modelled=flag)
        members = run.pipeline.candidates[run.pipeline.candidates.structural_candidate]
        assert set(members.strategy_id) == MVP_STRATEGY_IDS
        assert members.set_index("strategy_id").loc["ASCEND_STAKE_A0G", "allocation_gate"] == "CLOSED"
        assert "ASCEND_STAKE_A0G" not in run.pipeline.result.allocations
        assert run.to_dict()["schema_version"] == "1.3"
        assert run.to_dict()["input"]["include_modelled"] is flag
        allocations.append(run.pipeline.result.allocations)
        print_live_run(run)
        output = capsys.readouterr().out
        scope_lines.append(next(line for line in output.splitlines() if "Scope:" in line))
        assert "configured five-strategy universe (allocation gates apply)" in output
        assert "live + explicitly modelled routes" not in output
        assert "live routes only" not in output
    assert allocations[0] == allocations[1]
    assert scope_lines[0] == scope_lines[1]


def test_include_modelled_help_describes_compatibility_only(monkeypatch, capsys) -> None:
    from src.ascend_optimizer.live_optimize import main

    monkeypatch.setattr("sys.argv", ["live_optimize", "--help"])
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 0
    help_text = " ".join(capsys.readouterr().out.split())
    assert "Compatibility flag only; does not change the strategy universe or allocation gates." in help_text
    assert "Include MODELLED/PARTIAL_MODELLED Ascend routes" not in help_text
