"""SYNTHETIC_EVALUATION_ONLY. No observations, wallets, RPC or admission captures."""
from copy import deepcopy
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import json

import pytest

from src.ascend_optimizer import economics_evidence as e
from src.ascend_optimizer.amount_optimizer import AdmissionEvidence, AdmissionState, run_amount_optimizer, evaluate_candidate, candidate_grid
from src.ascend_optimizer.data_loader import load_strategies, load_snapshots, DEFAULT_DATA_DIR
from src.ascend_optimizer.profiles import get_profile

NATIVE = "NATIVE_STAKE_0G"
GIMO = "GIMO_STAKE_0G"
JAINE = "JAINE_LP_0G_USDC"
OKU = "OKU_LP_0G_USDC"
ASCEND = "ASCEND_STAKE_A0G"
NOW = datetime(2026, 10, 9, 14, 30, tzinfo=timezone.utc)
SCENARIO = "iteration19-test-only"


def common(sid=NATIVE):
    return dict(strategy_id=sid, evidence_class="MODELLED", source_id="test-scenario", source_role="EVALUATION_ASSUMPTION",
        source_verified=False, observation_timestamp=None, retrieval_timestamp=None, period_start=None, period_end=None,
        block_number=None, block_hash=None, chain_id=16661, amount_0g=None, amount_usd=None, config_context="test-config",
        capture_status="SYNTHETIC", scenario_id=SCENARIO, notes="SYNTHETIC_EVALUATION_ONLY")


def ret(sid=NATIVE, **changes):
    r = common(sid) | dict(evidence_id=sid+"-return", metric="gross_apy", value="0.1", unit="FRACTION_PER_YEAR",
        fee_basis="NET_OF_PROTOCOL_FEES", fees_embedded=["protocol_fee"], return_components=["base_yield"],
        incentive_policy="EXCLUDED_NO_REALIZABLE_EVIDENCE", economically_realizable=False, compounding_periods_per_year=365)
    return r | changes


def cost(sid=NATIVE, name="entry_gas", **changes):
    r = common(sid) | dict(evidence_id=sid+"-"+name, cost_type=name, structure="FIXED_PER_ENTRY", value="2", unit="USD",
        structural_zero_basis=None, horizon_days=None, quote_id=None)
    return r | changes


def zero(sid=NATIVE, name="bridge_cost"):
    return cost(sid, name, evidence_class="STATIC_CONFIG", capture_status="STATIC", scenario_id=None,
                source_verified=True, source_id="test-structural-spec", structure="STRUCTURAL_ZERO", value="0",
                structural_zero_basis="Synthetic test assertion of no user capital bridge; not an observed route")


def quote(sid=JAINE, direction="ENTRY", amount="100", **changes):
    r = common(sid) | dict(quote_id=sid+direction+amount, venue="JAINE" if sid == JAINE else "OKU", direction=direction,
        path="test-"+direction, token_in="W0G" if direction == "ENTRY" else "USDC.e",
        token_out="USDC.e" if direction == "ENTRY" else "W0G", market_context="test-pool-"+sid,
        fee_tier=3000, quoted_output="49", output_unit="USDC.e" if direction == "ENTRY" else "0G",
        slippage_rate="0.001", configuration_binding="SYNTHETIC_SCENARIO", quote_validity_state="UNASSESSED",
        embedded_cost_types=["lp_swap_fee"], amount_0g=amount)
    return r | changes


def valuation():
    return dict(price_usd="1", evidence_class="MODELLED", source_id="explicit-test-price-override",
                source_verified=False, observation_timestamp=None, retrieval_timestamp=None, scenario_id=SCENARIO)


def observed(r, cls="LIVE_OBSERVED", age=5):
    return r | dict(evidence_class=cls, capture_status="CAPTURED", source_verified=True, scenario_id=None,
                    observation_timestamp=(NOW-timedelta(seconds=age)).isoformat(), retrieval_timestamp=NOW.isoformat())


def normalization(**changes):
    return dict(strategy_id=NATIVE, amount_0g="100", price_usd="1", horizon_days=90, mode=e.SYNTHETIC,
                scenario_id=SCENARIO, config_context="test-config", as_of=NOW) | changes


def quote_args(q, **changes):
    return dict(strategy_id=q["strategy_id"], amount_0g=q["amount_0g"], direction=q["direction"], path=q["path"],
        market_context=q["market_context"], config_context=q["config_context"], mode=e.SYNTHETIC,
        scenario_id=SCENARIO, as_of=NOW) | changes


def provider(sids=(NATIVE,), *, amount_costs=(), quotes=(), mode=e.SYNTHETIC):
    costs = []
    for sid in sids:
        costs += [cost(sid)] + [zero(sid, name) for name in sorted(e.REQUIRED_COSTS[sid] - {"entry_gas"})]
    contexts = {sid: {"config_context": "test-config"} for sid in sids}
    for q in quotes:
        contexts[q["strategy_id"]][q["direction"]] = {k:q[k] for k in ("path", "market_context", "token_in", "token_out", "fee_tier", "output_unit")}
    return e.EconomicsProvider(returns=[ret(sid) for sid in sids], costs=costs+list(amount_costs), quotes=quotes,
        mode=mode, scenario_id=SCENARIO if mode == e.SYNTHETIC else None, valuation=valuation(), contexts=contexts)


@pytest.mark.parametrize("kind,make", [("return",ret), ("quote",quote), ("cost",cost)])
def test_schema_exact_fields_and_finite_numbers(kind, make):
    r = make(); assert e.validate_record(r,kind) == r
    bad = deepcopy(r); bad["unrecognized"] = 1
    with pytest.raises(e.EconomicsError): e.validate_record(bad,kind)
    bad = deepcopy(r); del bad["observation_timestamp"]
    with pytest.raises(e.EconomicsError): e.validate_record(bad,kind)
    bad = deepcopy(r); bad["quoted_output" if kind == "quote" else "value"] = "NaN"
    with pytest.raises(e.EconomicsError): e.validate_record(bad,kind)


@pytest.mark.parametrize("field,value", [("observation_timestamp",None), ("retrieval_timestamp",None),
    ("observation_timestamp","2026-10-09T00:00:00"), ("block_number",-1), ("block_hash","made-up"), ("chain_id",16602)])
def test_observation_fields_no_timestamp_fallback(field,value):
    r = observed(ret()); r[field] = value
    with pytest.raises(e.EconomicsError): e.validate_record(r,"return")


def test_observation_and_retrieval_are_distinct_and_age_uses_observation():
    r = observed(ret(), age=100)
    assert r["observation_timestamp"] != r["retrieval_timestamp"]
    policy = {("return",r["source_id"],r["metric"]): {"max_age_seconds":60,"rationale":"Synthetic source-specific test budget"}}
    assert e.qualify(r,"return",mode=e.PRODUCTION,scenario_id=None,as_of=NOW,policies=policy) == "STALE"
    assert e.qualify(r,"return",mode=e.PRODUCTION,scenario_id=None,as_of=NOW,policies={}) == "NO_VALID_POLICY"
    r["retrieval_timestamp"] = (NOW-timedelta(seconds=101)).isoformat()
    with pytest.raises(e.EconomicsError,match="retrieval precedes"): e.validate_record(r,"return")


@pytest.mark.parametrize("cls,state", [("HISTORICAL","HISTORICAL_NOT_CURRENT"), ("MODELLED","SYNTHETIC_MODE_REQUIRED")])
def test_history_and_models_not_current_live(cls,state):
    r = observed(ret(), cls=cls) if cls == "HISTORICAL" else ret()
    assert e.qualify(r,"return",mode=e.PRODUCTION,scenario_id=None,as_of=NOW,policies={}) == state
    assert e.qualify(r,"return",mode=e.SYNTHETIC,scenario_id=SCENARIO,as_of=NOW,policies={}) == "VALID"
    assert r["evidence_class"] == cls


def test_modelled_return_explicit_mode_and_scenario():
    with pytest.raises(e.EconomicsError,match="SYNTHETIC_MODE_REQUIRED"):
        e.normalize_return([ret()],**normalization(mode=e.PRODUCTION,scenario_id=None))
    with pytest.raises(e.EconomicsError):
        e.normalize_return([ret()],**normalization(scenario_id="different"))


@pytest.mark.parametrize("metric,role", [
    ("validator_yield_benchmark", "CONFIGURED_VALIDATOR_RETURN"),
    ("gross_apy", "VALIDATOR_OBSERVATIONAL_SAMPLE"),
])
def test_native_production_base_must_be_configured_validator(metric, role):
    r = observed(ret(metric=metric, source_role=role))
    policy = {("return", r["source_id"], metric): {"max_age_seconds": 60, "rationale": "Test-only budget"}}
    with pytest.raises(e.EconomicsError, match="NATIVE_BENCHMARK_NOT_CONFIGURED_ROUTE"):
        e.normalize_return([r], **normalization(mode=e.PRODUCTION, scenario_id=None, policies=policy))


@pytest.mark.parametrize("fee_basis,deduction,net", [
    ("GROSS_BEFORE_FEES", 1, 9),
    ("NET_OF_PROTOCOL_FEES", 0, 10),
])
def test_native_production_separate_commission_role(fee_basis, deduction, net):
    base = observed(ret(source_role="CONFIGURED_VALIDATOR_RETURN", fee_basis=fee_basis,
                        fees_embedded=[] if fee_basis == "GROSS_BEFORE_FEES" else ["commission"]))
    commission = observed(ret(evidence_id="native-commission", metric="commission", unit="FRACTION",
                              source_id="test-commission-source", source_role="CONFIGURED_VALIDATOR_COMMISSION",
                              fee_basis=fee_basis))
    policies = {("return", r["source_id"], r["metric"]):
                {"max_age_seconds": 60, "rationale": "Test-only budget"} for r in (base, commission)}
    result = e.normalize_return([base, commission], **normalization(
        mode=e.PRODUCTION, scenario_id=None, horizon_days=365, policies=policies))
    assert result["qualification"] == "VALID"
    assert result["expected_gross_income_usd"] == pytest.approx(10)
    assert result["additional_fee_usd"] == pytest.approx(deduction)
    assert result["income_after_protocol_fee_usd"] == pytest.approx(net)
    assert result["provenance"][1]["source_role"] == "CONFIGURED_VALIDATOR_COMMISSION"


@pytest.mark.parametrize("changes,error", [
    ({"source_verified": False}, "SOURCE_UNVERIFIED"),
    ({"observation_timestamp": (NOW-timedelta(seconds=61)).isoformat()}, "STALE"),
    ({"config_context": "other-validator"}, "CONTEXT_MISMATCH"),
])
def test_native_separate_commission_still_requires_qualification(changes, error):
    base = observed(ret(source_role="CONFIGURED_VALIDATOR_RETURN", fee_basis="GROSS_BEFORE_FEES", fees_embedded=[]))
    commission = observed(ret(evidence_id="native-commission", metric="commission", unit="FRACTION",
                              source_role="CONFIGURED_VALIDATOR_COMMISSION")) | changes
    policies = {("return", r["source_id"], r["metric"]):
                {"max_age_seconds": 60, "rationale": "Test-only budget"} for r in (base, commission)}
    with pytest.raises(e.EconomicsError, match=error):
        e.normalize_return([base, commission], **normalization(
            mode=e.PRODUCTION, scenario_id=None, policies=policies))


def test_native_sample_never_configured_route_return():
    r = observed(ret(metric="validator_yield_benchmark", source_role="VALIDATOR_OBSERVATIONAL_SAMPLE"))
    policy = {("return",r["source_id"],r["metric"]): {"max_age_seconds":60,"rationale":"Test-only budget"}}
    with pytest.raises(e.EconomicsError,match="NATIVE_BENCHMARK"):
        e.normalize_return([r],**normalization(mode=e.PRODUCTION,scenario_id=None,policies=policy))
    result = e.normalize_return([r],**normalization(policies=policy))
    assert result["base_apy"] == .1
    assert result["provenance"][0]["source_role"] == "VALIDATOR_OBSERVATIONAL_SAMPLE"


@pytest.mark.parametrize("sid", [GIMO,ASCEND])
def test_exchange_rate_growth_net_fee_no_double_count(sid):
    start = observed(ret(sid, metric="exchange_rate", unit="0G_PER_SHARE", value="1"), cls="HISTORICAL", age=365*86400)
    end = observed(ret(sid, evidence_id=sid+"-rate-end", metric="exchange_rate", unit="0G_PER_SHARE", value="1.1"), cls="HISTORICAL", age=0)
    fee = ret(sid, evidence_id=sid+"-fee", metric="protocol_fee_rate", unit="FRACTION", value="0.1",
              evidence_class="STATIC_CONFIG",capture_status="STATIC",source_verified=True,scenario_id=None)
    result = e.normalize_return([start,end,fee], **normalization(strategy_id=sid,horizon_days=365))
    assert result["base_apy"] == pytest.approx(.1)
    assert result["expected_gross_income_usd"] == pytest.approx(10)
    assert result["additional_fee_usd"] == 0
    assert result["evidence_classes"] == ["HISTORICAL","STATIC_CONFIG"]
    assert result["fees_already_embedded"] == ["protocol_fee"]
    with pytest.raises(e.EconomicsError,match="INSUFFICIENT_RATE_HISTORY"):
        e.normalize_return([end],**normalization(strategy_id=sid))


def test_lp_fee_apr_separate_from_quote_and_compounding_explicit():
    r = ret(JAINE, metric="lp_fee_apr", value="0.12", compounding_periods_per_year=1)
    result = e.normalize_return([r],**normalization(strategy_id=JAINE,horizon_days=365))
    assert result["base_apy"] == pytest.approx(.12)
    with pytest.raises(e.EconomicsError): e.validate_record(quote(),"return")


def test_holding_period_return_and_period_requirements():
    r = ret(metric="holding_period_return",unit="FRACTION", value="0.05",
        period_start=(NOW-timedelta(days=90)).isoformat(), period_end=NOW.isoformat())
    result = e.normalize_return([r],**normalization())
    assert result["expected_gross_income_usd"] == pytest.approx(5)
    with pytest.raises(e.EconomicsError): e.validate_record(r | {"period_end":None},"return")


def test_gross_fee_deducted_once_and_unknown_fee_not_defaulted():
    base = ret(fee_basis="GROSS_BEFORE_FEES", fees_embedded=[])
    fee = ret(metric="protocol_fee_rate",unit="FRACTION",value=".1",evidence_id="fee")
    result = e.normalize_return([base,fee],**normalization(horizon_days=365))
    assert result["additional_fee_usd"] == pytest.approx(1)
    with pytest.raises(e.EconomicsError,match="MISSING_OR_AMBIGUOUS"):
        e.normalize_return([base],**normalization())


def test_embedded_yield_and_lp_nav_reward_double_counts_rejected():
    for sid in (ASCEND,JAINE,OKU):
        base = ret(sid,incentive_policy="REQUIRE_REALIZABLE_EVIDENCE",return_components=["embedded_yield"])
        incentive = ret(sid,metric="incentive_apy",evidence_id=sid+"-extra",economically_realizable=True,return_components=["embedded_yield"])
        with pytest.raises(e.EconomicsError,match="DOUBLE_COUNT"):
            e.normalize_return([base,incentive],**normalization(strategy_id=sid))
    with pytest.raises(e.EconomicsError,match="DOUBLE_COUNTED_RETURN"):
        e.normalize_return([ret(ASCEND),ret(ASCEND,evidence_id="restaking",metric="gross_apr")],**normalization(strategy_id=ASCEND))


def test_points_excluded_and_realizable_incentive_needs_proof():
    points = ret(metric="points",unit="NON_FINANCIAL",value="100000",evidence_id="points")
    result = e.normalize_return([ret(),points],**normalization())
    assert result["incentive_apy"] == 0
    assert result["excluded_nonfinancial_points"] == ["points"]
    base = ret(incentive_policy="REQUIRE_REALIZABLE_EVIDENCE")
    with pytest.raises(e.EconomicsError,match="MISSING_REALIZABLE"):
        e.normalize_return([base,points],**normalization())
    incentive = ret(metric="incentive_apy",evidence_id="financial",value=".02",economically_realizable=True,return_components=["separate_redeemable"])
    result = e.normalize_return([base,incentive],**normalization())
    assert result["incentive_apy"] == .02


@pytest.mark.parametrize("field,value,state", [("amount_0g","100.000000000000000001","AMOUNT_MISMATCH"),
    ("strategy_id",OKU,"CONTEXT_MISMATCH"), ("direction","EXIT","CONTEXT_MISMATCH"),
    ("path","different","CONTEXT_MISMATCH"), ("market_context","different","CONTEXT_MISMATCH"),
    ("config_context","different","CONTEXT_MISMATCH")])
def test_quote_exact_decimal_and_independent_context(field,value,state):
    q = quote(); args = quote_args(q); args[field]=value
    assert e.assess_quote(q,**args)["validity"] == state
    assert e.assess_quote(q,**quote_args(q,amount_0g=Decimal("100.0")))["validity"] == "VALID"


@pytest.mark.parametrize("age,expected", [(30,"VALID"),(60,"VALID"),(61,"STALE")])
def test_observational_quote_own_test_policy(age,expected):
    q = observed(quote(),age=age) | {"configuration_binding":"UNBOUND_TO_DEPLOYED_ROUTE"}
    policy = {("quote",q["source_id"],"ENTRY"): {"max_age_seconds":60,"rationale":"SYNTHETIC test budget, not canonical policy"}}
    assessment = e.assess_quote(q,**quote_args(q,policies=policy))
    assert assessment["validity"] == expected
    assert assessment["technical_admission"] == assessment["capacity"] == "NOT_ASSESSED"
    assert assessment["configuration_binding"] == "UNBOUND_TO_DEPLOYED_ROUTE"


def test_quote_policy_undefined_unverified_and_unbound():
    q = observed(quote()) | {"configuration_binding":"UNBOUND_TO_DEPLOYED_ROUTE"}
    assert e.assess_quote(q,**quote_args(q))["validity"] == "POLICY_UNDEFINED"
    q["source_verified"] = False
    assert e.assess_quote(q,**quote_args(q))["validity"] == "SOURCE_UNVERIFIED"
    q["source_verified"] = True
    policy = {("quote",q["source_id"],"ENTRY"): {"max_age_seconds":60,"rationale":"Test budget"}}
    assert e.assess_quote(q,**quote_args(q,mode=e.PRODUCTION,scenario_id=None,policies=policy))["validity"] == "CONTEXT_MISMATCH"
    assert e.assess_quote(None,**quote_args(q))["validity"] == "MISSING"


def test_missing_quote_record_and_embedded_swap_fee_coverage():
    missing = quote(evidence_class="MISSING",capture_status="MISSING",quoted_output=None,amount_0g=None)
    assert e.assess_quote(missing,**quote_args(quote()))["validity"] == "MISSING"
    with pytest.raises(e.EconomicsError,match="swap fee"):
        e.validate_record(quote(embedded_cost_types=[]),"quote")


def test_duplicate_loader_identity_and_missing_keys(tmp_path):
    path=tmp_path/"returns.json"
    path.write_text(json.dumps({"schema_version":"ECONOMICS_EVIDENCE_V1","kind":"return","records":[ret(),ret()]}))
    with pytest.raises(e.EconomicsError,match="duplicate"): e.load_evidence(path,"return")
    path.write_text(json.dumps({"schema_version":"ECONOMICS_EVIDENCE_V1","kind":"cost","records":[]}))
    with pytest.raises(e.EconomicsError,match="envelope"): e.load_evidence(path,"return")


def test_live_derived_return_preserves_observed_provenance_and_own_policy():
    r=observed(ret(GIMO))
    policy={("return",r["source_id"],r["metric"]):{"max_age_seconds":60,"rationale":"Test-only source budget"}}
    result=e.normalize_return([r],**normalization(strategy_id=GIMO,mode=e.PRODUCTION,scenario_id=None,policies=policy))
    assert result["evidence_class"]=="LIVE_DERIVED"
    assert result["provenance"][0]["evidence_class"]=="LIVE_OBSERVED"
    with pytest.raises(e.EconomicsError,match="NO_VALID_POLICY"):
        e.normalize_return([r],**normalization(strategy_id=GIMO,mode=e.PRODUCTION,scenario_id=None))


def test_static_return_never_promoted_to_live_class():
    r=ret(GIMO,evidence_class="STATIC_CONFIG",capture_status="STATIC",source_verified=True,scenario_id=None)
    result=e.normalize_return([r],**normalization(strategy_id=GIMO))
    assert result["evidence_class"]=="STATIC_CONFIG"
    with pytest.raises(e.EconomicsError,match="STATIC_RETURN_NOT_CURRENT"):
        e.normalize_return([r],**normalization(strategy_id=GIMO,mode=e.PRODUCTION,scenario_id=None))


def test_future_observation_and_policy_rationale_rejected():
    r=observed(ret(),age=-1)
    with pytest.raises(e.EconomicsError): e.validate_record(r,"return")
    r=observed(ret())
    with pytest.raises(e.EconomicsError,match="rationale"):
        e.qualify(r,"return",mode=e.PRODUCTION,scenario_id=None,as_of=NOW,
                  policies={("return",r["source_id"],r["metric"]):{"max_age_seconds":60,"rationale":""}})


def test_cost_current_valuation_source_and_timestamp_policy():
    v=valuation()|dict(evidence_class="LIVE_OBSERVED",source_verified=True,scenario_id=None,
        observation_timestamp=(NOW-timedelta(seconds=5)).isoformat(),retrieval_timestamp=NOW.isoformat())
    r=zero(name="entry_gas")
    policies={("valuation",v["source_id"],"0G_USD"):{"max_age_seconds":60,"rationale":"Test-only price budget"}}
    result=e.normalize_costs([r],**normalization(policies=policies),valuation=v,required_costs={"entry_gas"})
    assert result["valuation"]["evidence_class"]=="LIVE_OBSERVED"
    with pytest.raises(e.EconomicsError,match="NO_VALID_POLICY"):
        e.normalize_costs([r],**normalization(),valuation=v,required_costs={"entry_gas"})
    with pytest.raises(e.EconomicsError,match="STALE"):
        e.normalize_costs([r],**normalization(policies=policies,as_of=NOW+timedelta(seconds=61)),valuation=v,required_costs={"entry_gas"})


def test_cost_coverage_override_is_test_only():
    with pytest.raises(e.EconomicsError,match="SYNTHETIC_ONLY"):
        e.normalize_costs([],**normalization(mode=e.PRODUCTION,scenario_id=None),valuation=valuation(),required_costs=set())


def test_realized_incentive_amount_horizon_and_no_interpolation():
    base=ret(incentive_policy="REQUIRE_REALIZABLE_EVIDENCE")
    incentive=ret(metric="realized_incentive",unit="USD",value="2",evidence_id="redeemable",amount_0g="100",
        economically_realizable=True,return_components=["redeemable_stream"],
        period_start=(NOW-timedelta(days=90)).isoformat(),period_end=NOW.isoformat())
    result=e.normalize_return([base,incentive],**normalization())
    assert result["realized_incentive_usd"]==2
    with pytest.raises(e.EconomicsError,match="AMOUNT_MISMATCH"):
        e.normalize_return([base,incentive],**normalization(amount_0g="200"))
    with pytest.raises(e.EconomicsError,match="HORIZON_MISMATCH"):
        e.normalize_return([base,incentive],**normalization(horizon_days=180))


def test_synthetic_quote_requires_explicit_scenario_never_public_binding():
    q = quote()
    assert e.assess_quote(q,**quote_args(q,mode=e.PRODUCTION,scenario_id=None))["validity"] == "SYNTHETIC_MODE_REQUIRED"
    assert e.assess_quote(q,**quote_args(q,scenario_id="other"))["validity"] == "SYNTHETIC_MODE_REQUIRED"
    with pytest.raises(e.EconomicsError): e.validate_record(q | {"configuration_binding":"BOUND_TO_VERIFIED_RUNTIME"},"quote")


def test_cost_fixed_once_variable_scales_and_conversion_provenance():
    rows = [cost(), cost(name="protocol_entry_fee",structure="VARIABLE_BPS",unit="BPS",value="25"),
            cost(name="native_withdrawal_fee",structure="FIXED_PER_EXIT",unit="0G",value="1")]
    for amount in ("100","400"):
        result = e.normalize_costs(rows,**normalization(amount_0g=amount),valuation=valuation(),required_costs=[r["cost_type"] for r in rows])
        assert result["fixed_cost_usd"] == 3
        assert result["total_cost_usd"] == 3+float(amount)*.0025
        assert result["components"][-1]["native_unit_amount"] == "1"
        assert result["components"][-1]["valuation"]["evidence_class"] == "MODELLED"


@pytest.mark.parametrize("kind,make", [("return",ret),("cost",cost)])
def test_missing_evidence_not_zero(kind,make):
    r = make(evidence_class="MISSING",capture_status="MISSING",value=None)
    assert e.qualify(r,kind,mode=e.PRODUCTION,scenario_id=None,as_of=NOW,policies={}) == "MISSING"
    with pytest.raises(e.EconomicsError): e.validate_record(r | {"value":"0"},kind)


@pytest.mark.parametrize("changes", [{"structure":"FIXED_PER_ENTRY","value":"0"},
    {"structure":"STRUCTURAL_ZERO","value":"0"}, {"structural_zero_basis":None}, {"source_verified":False}])
def test_zero_requires_explicit_structural_static_basis(changes):
    r = cost() | changes if "structure" in changes else zero() | changes
    with pytest.raises(e.EconomicsError): e.validate_record(r,"cost")


def test_explicit_structural_zero_and_missing_coverage():
    r = zero()
    result = e.normalize_costs([r],**normalization(),valuation=valuation(),required_costs={"bridge_cost"})
    assert result["total_cost_usd"] == 0
    assert result["components"][0]["evidence"]["structural_zero_basis"]
    with pytest.raises(e.EconomicsError,match="MISSING_COST"):
        e.normalize_costs([],**normalization(),valuation=valuation())


def test_valuation_and_amount_dependent_cost_require_exact_context():
    r = cost(structure="AMOUNT_DEPENDENT_QUOTE",amount_0g="100")
    with pytest.raises(e.EconomicsError,match="AMOUNT_MISMATCH"):
        e.normalize_costs([r],**normalization(amount_0g="101"),valuation=valuation(),required_costs={"entry_gas"})
    with pytest.raises(e.EconomicsError,match="VALUATION_MISMATCH"):
        e.normalize_costs([r],**normalization(price_usd="2"),valuation=valuation(),required_costs={"entry_gas"})
    with pytest.raises(e.EconomicsError,match="VALUATION"):
        e.normalize_costs([r],**normalization(),valuation=None,required_costs={"entry_gas"})


def test_quote_cost_and_return_cost_double_count_prevention():
    q = quote()
    r = cost(JAINE,"lp_swap_fee")
    with pytest.raises(e.EconomicsError,match="QUOTE_COST_DOUBLE_COUNT"):
        e.normalize_costs([r],**normalization(strategy_id=JAINE),valuation=valuation(),quotes=[q],required_costs={"lp_swap_fee"})
    r = cost(name="commission")
    with pytest.raises(e.EconomicsError,match="RETURN_COST_DOUBLE_COUNT"):
        e.normalize_costs([r],**normalization(),valuation=valuation(),required_costs={"commission"})


def test_quote_derived_cost_requires_valid_parent():
    q = observed(quote(),age=61) | {"configuration_binding":"UNBOUND_TO_DEPLOYED_ROUTE"}
    r = observed(cost(JAINE,"extra_execution",evidence_class="QUOTE_DERIVED",quote_id=q["quote_id"]),cls="QUOTE_DERIVED")
    policies = {("quote",q["source_id"],"ENTRY"): {"max_age_seconds":60,"rationale":"Test budget"},
                ("cost",r["source_id"],r["cost_type"]): {"max_age_seconds":60,"rationale":"Test budget"}}
    with pytest.raises(e.EconomicsError,match="INVALID_PARENT_QUOTE:STALE"):
        e.normalize_costs([r],**normalization(strategy_id=JAINE,policies=policies),valuation=valuation(),quotes=[q],required_costs={"extra_execution"})


def supported(**kw):
    return AdmissionEvidence(AdmissionState.SUPPORTED,str(kw["strategy"].strategy_id),kw["amount_0g"],16661,
                            "SYNTHETIC_EVALUATION_ONLY","Explicit test-only admission assumption","MODELLED")


def inputs():
    s = load_strategies(); snapshots = load_snapshots(s,DEFAULT_DATA_DIR / "demo_strategy_snapshots.csv")
    return s,snapshots


def run(p,**changes):
    s,snapshots = inputs()
    return run_amount_optimizer(s,snapshots,decision_amount=1000,price_usd=1,horizon_days=365,profile="Aggressive",
        as_of=NOW,admission_fn=supported,economics_fn=p,economics_mode=e.SYNTHETIC,**changes)


def test_integration_fixed_cost_once_negative_economics_and_serialization():
    p = provider()
    result = run(p)
    points = [c for c in result.candidates if c.strategy_id==NATIVE and c.weight>0]
    assert all(c.fixed_execution_cost_usd==2 for c in points)
    assert points[0].net_profit_usd == pytest.approx(8)
    assert points[3].net_profit_usd == pytest.approx(38)
    assert result.selected and result.revalidation == "PASSED"
    assert result.grid == candidate_grid(get_profile("Aggressive"))
    payload = result.to_dict(); encoded = json.loads(json.dumps(payload,allow_nan=False))
    assert encoded["recommendation"] == payload["recommendation"]
    assert encoded["proposed_selected"][0]["economics_evidence"] == payload["proposed_selected"][0]["economics_evidence"]
    assert payload["cost_basis"] == "CANONICAL_ECONOMICS_EVIDENCE_V1"
    p.costs[0]["value"]="200"
    negative = run(p)
    assert not negative.selected
    assert any(c.net_profit_usd is not None and c.net_profit_usd<0 for c in negative.candidates if c.weight>0)


def test_missing_required_cost_blocks_positive_and_models_cannot_unlock_production():
    p=provider(); p.costs=[r for r in p.costs if r["cost_type"]!="exit_gas"]
    result=run(p)
    assert not result.selected
    assert any("MISSING_COST" in str(c.rejection_reasons) for c in result.candidates)
    p=provider(mode=e.PRODUCTION)
    s,snapshots=inputs()
    result=run_amount_optimizer(s,snapshots,decision_amount=1000,price_usd=1,horizon_days=365,profile="Aggressive",
        as_of=NOW,admission_fn=supported,economics_fn=p)
    assert not result.selected
    assert any("SYNTHETIC_MODE_REQUIRED" in str(c.rejection_reasons) for c in result.candidates)


def test_amount_specific_cost_changes_ranking_without_grid_change():
    p=provider()
    p.costs=[r for r in p.costs if r["cost_type"]!="entry_gas"]
    for amount in range(100,801,100):
        p.costs.append(cost(structure="AMOUNT_DEPENDENT_QUOTE",amount_0g=str(amount),value="1" if amount<=400 else "100"))
    result=run(p)
    assert result.selected[0].weight==.4
    assert result.grid==candidate_grid(get_profile("Aggressive"))


def test_lp_quotes_per_exact_candidate_no_quote_no_positive():
    qs=[quote(JAINE,d,str(amount)) for amount in range(100,801,100) for d in ("ENTRY","EXIT")]
    p=provider((JAINE,),quotes=qs)
    result=run(p)
    assert result.selected[0].strategy_id==JAINE
    assert result.revalidation=="PASSED"
    p.quotes=[]
    assert not run(p).selected
    p=provider((JAINE,),quotes=qs[:2])
    result=run(p)
    assert result.selected[0].amount_0g==100
    assert all(not c.eligible for c in result.candidates if c.strategy_id==JAINE and c.amount_0g>100)


@pytest.mark.parametrize("change", ["identity","source","context","price","amount"])
def test_selected_point_economic_revalidation_fails_on_evidence_change(change):
    p=provider()
    def fn(**kw):
        if kw["stage"]=="REVALIDATION":
            if change=="identity": p.returns[0]["evidence_id"]="changed"
            elif change=="source": p.returns[0]["source_id"]="changed"
            elif change=="context": p.returns[0]["config_context"]="changed"
            elif change=="price": p.valuation["price_usd"]="2"
            else: p.costs[0]["amount_0g"]="123"
        return p(**kw)
    result=run(fn)
    assert result.revalidation=="FAILED"
    assert result.to_dict()["recommendation"] is None


def test_selected_quote_expiry_and_identity_revalidation():
    qs=[quote(JAINE,d,str(amount)) for amount in range(100,801,100) for d in ("ENTRY","EXIT")]
    p=provider((JAINE,),quotes=qs)
    def fn(**kw):
        if kw["stage"]=="REVALIDATION":
            p.quotes=[q|{"quote_id":q["quote_id"]+"-replacement"} for q in p.quotes]
        return p(**kw)
    assert run(fn).revalidation=="FAILED"
    # Observational quotes with an explicitly test-only policy expire at a later
    # selected-point time. Economics source/record hashes do not change.
    p=provider((JAINE,),quotes=[observed(q)|{"configuration_binding":"UNBOUND_TO_DEPLOYED_ROUTE"} for q in qs])
    p.policies={("quote","test-scenario",d):{"max_age_seconds":60,"rationale":"Test-only quote budget"} for d in ("ENTRY","EXIT")}
    result=run(p,revalidation_as_of=NOW+timedelta(seconds=61))
    assert result.revalidation=="FAILED"


def test_economics_does_not_create_admission_or_open_ascend():
    p=provider((NATIVE,ASCEND))
    s,snapshots=inputs()
    result=run_amount_optimizer(s,snapshots,decision_amount=1000,price_usd=1,horizon_days=365,profile="Aggressive",
        as_of=NOW,economics_fn=p,economics_mode=e.SYNTHETIC)
    assert not result.selected
    assert all(not c.eligible for c in result.candidates if c.strategy_id==ASCEND and c.weight>0)
    assert result.to_dict()["recommendation"]["idle_weight"]==1


@pytest.mark.parametrize("profile", ["Conservative","Balanced","Aggressive"])
def test_canonical_repository_empty_economics_and_idle(profile):
    p=e.EconomicsProvider.repository()
    assert p.returns==p.quotes==p.costs==[]
    s,snapshots=inputs()
    result=run_amount_optimizer(s,snapshots,decision_amount=1000,price_usd=1,horizon_days=90,profile=profile,as_of=NOW)
    assert result.to_dict()["recommendation"]["idle_weight"]==1
    assert not result.selected
    config=json.loads((DEFAULT_DATA_DIR/"runtime_strategy_config.json").read_text())
    assert all(r["verification_state"]=="UNRESOLVED" and r["config_identity"] is None for r in config["records"])
    assert len((DEFAULT_DATA_DIR/"admission_evidence.csv").read_text().splitlines())==1
    assert s.loc[s.strategy_id==ASCEND,"allocation_gate"].item()=="CLOSED"
