"""Schema 1.3 contract tests use synthetic snapshots, never fresh collectors."""
import json

import pandas as pd
import pytest

from src.ascend_optimizer.data_loader import load_datasets, load_snapshots, load_strategies, MVP_STRATEGY_IDS
from src.ascend_optimizer.live_optimize import optimize_live
from src.ascend_optimizer.result_contract import strategy_contract


def run_demo(**kwargs):
    strategies = load_strategies()
    snapshots = load_snapshots(strategies, "data/demo_strategy_snapshots.csv")
    return optimize_live(strategies, snapshots, amount=1000, horizon_days=90,
                         profile="Balanced", price_usd=1, **kwargs)


def test_schema_state_scope_and_legacy_aliases_are_consistent():
    payload = run_demo().to_dict()
    assert payload["schema_version"] == "1.3"
    assert payload["run_scope"] == {"capital_scope": "DECISION_SLEEVE", "constraint_scope": "DECISION_SLEEVE", "whole_portfolio_compliance": "NOT_ASSESSED"}
    assert payload["portfolio"]["scope"] == payload["profile_constraints"]["scope"] == "DECISION_SLEEVE"
    inputs = payload["input"]
    assert inputs["decision_asset"] == inputs["asset"] == "0G"
    assert inputs["decision_amount"] == inputs["amount"] == 1000
    assert inputs["decision_value_usd"] == inputs["portfolio_value_usd"] == 1000
    assert inputs["submitted"]["decision_amount"] == 1000
    rows = {r["strategy_id"]: r for r in payload["strategies"]}
    assert {sid for sid,r in rows.items() if r["structural_candidate"]} == MVP_STRATEGY_IDS
    for sid in MVP_STRATEGY_IDS:
        row = rows[sid]
        assert row["optimizer_universe"] == "TRUE"
        assert row["protocol_availability"] == "LIVE"
        assert row["integration_status"] == "IMPLEMENTED"
        assert row["execution_readiness"] == row["live_capstone_proof"] == "NOT_ESTABLISHED"
        assert row["runtime_feasibility"] == "NOT_ASSESSED"
    jaine = rows["JAINE_LP_0G_USDC"]
    assert jaine["allocation_gate"] == "CONDITIONAL"
    assert jaine["allocation_admitted"]
    assert jaine["allocation_result"] == "ALLOCATED_POSITIVE"
    assert jaine["evidence_readiness"] == "NOT_ASSESSED"
    ascend = rows["ASCEND_STAKE_A0G"]
    assert ascend["reconciliation_category"] == "INTEGRATED_GATED"
    assert ascend["allocation_gate"] == "CLOSED"
    assert not ascend["allocation_admitted"]
    assert ascend["allocation_weight"] == 0
    assert ascend["allocation_result"] == "GATED"
    assert "ALLOCATION_GATE_CLOSED" in {r["code"] for r in ascend["reasons"]}
    for sid in ("ASCEND_RESTAKE", "MORPHO_LEND_0G"):
        assert rows[sid]["optimizer_universe"] == "FALSE"
        assert rows[sid]["allocation_result"] == "NOT_CANDIDATE"
        assert rows[sid]["net_return_horizon"] is None
        assert "NOT_IN_OPTIMIZER_UNIVERSE" in {r["code"] for r in rows[sid]["reasons"]}
    assert rows["ASCEND_RESTAKE"]["parent_strategy_id"] == "ASCEND_STAKE_A0G"
    assert payload["outcome"]["execution_readiness"] == "NOT_ESTABLISHED"
    assert payload["outcome"]["live_capstone_proof"] == "NOT_ESTABLISHED"


def test_eligible_zero_is_not_exclusion_or_invented_economic_cause():
    native = next(r for r in run_demo().to_dict()["strategies"] if r["strategy_id"] == "NATIVE_STAKE_0G")
    assert native["profile_eligible"]
    assert native["allocation_result"] == "ELIGIBLE_ZERO"
    assert native["exclusion_reasons"] == []
    assert native["reasons"][0]["code"] == "ELIGIBLE_ZERO_ALLOCATION"
    assert native["reasons"][0]["kind"] == "ALLOCATION_RESULT"


def test_valuation_mode_is_known_but_provenance_and_validity_are_not_invented():
    override = run_demo().to_dict()
    assert override["valuation"] == {"asset": "0G", "price_usd": 1, "decision_value_usd": 1000, "acquisition_mode": "USER_OVERRIDE", "provenance_status": "NOT_REPRESENTED"}
    strategies = load_strategies(); snapshots = load_snapshots(strategies,"data/demo_strategy_snapshots.csv")
    fetched = optimize_live(strategies,snapshots,amount=1000,horizon_days=90,profile="Balanced",price_fn=lambda: 2).to_dict()
    assert fetched["valuation"]["acquisition_mode"] == "FETCHED"
    assert fetched["valuation"]["decision_value_usd"] == 2000
    assert fetched["input"]["submitted"]["price_usd_override"] is None
    assert "observation_timestamp" not in fetched["valuation"]
    assert "valid" not in fetched["valuation"]


def test_no_positive_allocation_outcome_does_not_claim_qualified_evidence():
    bundle = load_datasets()
    payload = optimize_live(bundle.strategies,bundle.snapshots,amount=1000,horizon_days=90,profile="Balanced",price_usd=1).to_dict()
    assert payload["outcome"]["state"] == "NO_POSITIVE_ALLOCATION"
    assert payload["portfolio"]["idle"]["weight"] == 1
    assert payload["outcome"]["execution_readiness"] == "NOT_ESTABLISHED"
    assert {"MISSING_RETURN_DATA", "MISSING_EXPOSURE_DATA"} <= {r["code"] for s in payload["strategies"] for r in s["reasons"]}
    assert json.loads(json.dumps(payload,allow_nan=False)) == payload


def test_flag_and_serialization_do_not_mutate_solver_result_or_submitted_context():
    off = run_demo(); on = run_demo(include_modelled=True)
    before = off.pipeline.candidates.copy(deep=True)
    result = off.pipeline.result
    p1 = off.to_dict(); p2 = on.to_dict()
    assert p1["portfolio"] == p2["portfolio"]
    assert p1["strategies"] == p2["strategies"]
    assert p2["input"]["include_modelled"] is True
    assert off.pipeline.result is result
    pd.testing.assert_frame_equal(before, off.pipeline.candidates)
    p1["input"]["submitted"]["decision_amount"] = 99
    assert off.to_dict()["input"]["submitted"]["decision_amount"] == 1000
    json.dumps(p2,allow_nan=False)


@pytest.mark.parametrize("legacy,code", [
    ("slippage_exceeds_profile_limit", "PROFILE_SLIPPAGE_LIMIT"),
    ("exit_time_exceeds_profile_limit", "PROFILE_EXIT_TIME_LIMIT"),
    ("no_usable_liquidity", "LEGACY_LIQUIDITY_BOUND"),
])
def test_typed_reasons_preserve_actual_runtime_source(legacy,code):
    run=run_demo(); row=run.pipeline.candidates.iloc[0]
    state=strategy_contract(row,weight=0,profile_eligible=False,optimizer_eligible=True,legacy_reasons=[legacy])
    assert code in {r["code"] for r in state["reasons"]}


def test_runtime_quote_failure_is_not_relabelled_as_profile_risk():
    row=run_demo().pipeline.candidates.iloc[0].copy()
    row["runtime_exposure_error"]="quote unavailable"
    state=strategy_contract(row,weight=0,profile_eligible=False,optimizer_eligible=False,legacy_reasons=[])
    assert any(r["code"]=="RUNTIME_QUOTE_UNAVAILABLE" and r["detail"]=="quote unavailable" for r in state["reasons"])


def test_submitted_labels_are_preserved_separately_from_resolved_inputs():
    strategies=load_strategies(); snapshots=load_snapshots(strategies,"data/demo_strategy_snapshots.csv")
    payload=optimize_live(strategies,snapshots,amount=1000,horizon_days=90,profile="balanced",asset=" 0G ",price_usd=1).to_dict()
    assert payload["input"]["submitted"]["profile"] == "balanced"
    assert payload["input"]["submitted"]["decision_asset"] == " 0G "
    assert payload["input"]["profile"] == "Balanced"
    assert payload["input"]["decision_asset"] == "0G"
