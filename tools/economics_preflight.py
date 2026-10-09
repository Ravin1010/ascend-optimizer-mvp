"""Read-only Iteration 19 report. No RPC, collection, signing or file writes.

Default: canonical repository evidence, no synthetic admission.
--synthetic: additionally replay explicitly labelled test-only economic cases.
Price/amount/H are analysis inputs, not current observed financial evidence.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.ascend_optimizer.amount_optimizer import run_amount_optimizer
from src.ascend_optimizer.data_loader import load_strategies, load_snapshots, DEFAULT_DATA_DIR
from src.ascend_optimizer import economics_evidence as e

AS_OF = datetime(2026, 10, 9, 14, 30, tzinfo=timezone.utc)


def repository_baseline():
    strategies = load_strategies()
    snapshots = load_snapshots(strategies, DEFAULT_DATA_DIR / "strategy_snapshots.csv")
    provider = e.EconomicsProvider.repository()
    rows = []
    for profile in ("Conservative", "Balanced", "Aggressive"):
        run = run_amount_optimizer(strategies, snapshots, decision_amount=1000, price_usd=1,
                                   horizon_days=90, profile=profile, as_of=AS_OF)
        rows.append({"profile": profile, "qualified_return_evidence": "MISSING",
                     "qualified_quote_cost_evidence": "MISSING", "allocation": [],
                     "idle_weight": run.to_dict()["recommendation"]["idle_weight"],
                     "main_reason": "UNRESOLVED_RUNTIME_CONFIG_AND_EMPTY_ADMISSION",
                     "positive_selected_count": len(run.selected)})
    return {"as_of": AS_OF.isoformat(), "evidence_mode": e.PRODUCTION,
            "return_record_count": len(provider.returns), "quote_record_count": len(provider.quotes),
            "cost_record_count": len(provider.costs), "freshness_policies": "NO_VALID_SOURCE_POLICY",
            "analysis_inputs": {"amount_0g": "1000", "price_usd": "1", "price_basis": "MODELLED_ANALYSIS_ONLY_NOT_QUALIFIED", "horizon_days": 90},
            "runs": rows, "public_deployment_required": False, "public_deployment_planned": False}


def synthetic_verification():
    # Reuse ephemeral test fixtures, never canonical records. This tool's optional
    # branch is a test replay, not an ingestion/production evaluation command.
    t = runpy.run_path(str(ROOT / "tests/test_economics_evidence.py"))
    p = t["provider"]()
    run = t["run"](p)
    points = [c for c in run.candidates if c.strategy_id == t["NATIVE"] and c.weight > 0]
    variable = []
    r = t["cost"](name="protocol_entry_fee", structure="VARIABLE_BPS", unit="BPS", value="25")
    for amount in ("100", "400"):
        result = e.normalize_costs([r], **t["normalization"](amount_0g=amount), valuation=t["valuation"](), required_costs={"protocol_entry_fee"})
        variable.append({"amount_0g": amount, "variable_cost_usd": result["total_cost_usd"]})
    cases = []
    for name in (
        "test_missing_required_cost_blocks_positive_and_models_cannot_unlock_production",
        "test_explicit_structural_zero_and_missing_coverage",
        "test_embedded_yield_and_lp_nav_reward_double_counts_rejected",
        "test_points_excluded_and_realizable_incentive_needs_proof",
        "test_synthetic_quote_requires_explicit_scenario_never_public_binding",
        "test_amount_specific_cost_changes_ranking_without_grid_change",
        "test_lp_quotes_per_exact_candidate_no_quote_no_positive",
        "test_selected_quote_expiry_and_identity_revalidation",
        "test_economics_does_not_create_admission_or_open_ascend",
    ):
        t[name]()
        cases.append({"test": name, "result": "PASS"})
    for sid in (t["GIMO"], t["ASCEND"]):
        t["test_exchange_rate_growth_net_fee_no_double_count"](sid)
        cases.append({"test": "exchange_rate_growth_net_fee_no_double_count", "strategy_id": sid, "result": "PASS",
                      "assumed_one_year_rate_growth": "1 -> 1.1", "derived_apy": .1, "additional_protocol_fee_usd": 0})
    q = t["quote"]()
    wrong = e.assess_quote(q, **t["quote_args"](q, amount_0g="100.000000000000000001"))
    t["test_selected_point_economic_revalidation_fails_on_evidence_change"]("identity")
    return {"label": e.SYNTHETIC, "source": "tests/test_economics_evidence.py; ephemeral fixtures only",
            "scenario_id": t["SCENARIO"], "native_candidates": [{"amount_0g": str(c.amount_0g),
                "fixed_cost_usd": c.fixed_execution_cost_usd, "net_profit_usd": c.net_profit_usd} for c in points],
            "variable_cost_cases": variable, "quote_exact_amount_failure": wrong["validity"],
            "selected_point_revalidation": run.revalidation, "changed_selected_evidence_test": "PASS",
            "cases": cases, "technical_admission_basis": "TEST_ONLY_ASSUMPTION", "risk_stress": "UNCHANGED_LEGACY_TEST_FIXTURE_COEFFICIENTS",
            "public_deployment_proof": "NOT_ESTABLISHED"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthetic", action="store_true", help="Explicit SYNTHETIC_EVALUATION_ONLY test replay")
    args = parser.parse_args()
    report = {"iteration": 19, "canonical_repository_baseline": repository_baseline()}
    if args.synthetic:
        report["synthetic_verification"] = synthetic_verification()
    print(json.dumps(report, indent=2, allow_nan=False))
