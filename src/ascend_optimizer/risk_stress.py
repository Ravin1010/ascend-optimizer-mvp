"""Deterministic synthetic stress budgets; independent of admission and economics.

The existing optimizers retain legacy constraints. This additive evaluation
primitive never turns modelled analysis into a production recommendation.
"""
from __future__ import annotations
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
import hashlib
import json
from pathlib import Path

from .data_loader import DEFAULT_DATA_DIR, MVP_STRATEGY_IDS
from . import lp_range_stress as lp
from .profiles import get_profile

VERSION = "RISK_STRESS_V1"
SCENARIO_VERSION = "RISK_SCENARIOS_V1"
LABEL = lp.LABEL
NATIVE, GIMO, JAINE, OKU, ASCEND = ('NATIVE_STAKE_0G', 'GIMO_STAKE_0G', 'JAINE_LP_0G_USDC', 'OKU_LP_0G_USDC', 'ASCEND_STAKE_A0G')
STRATEGIES = (NATIVE, GIMO, JAINE, OKU, ASCEND)
assert set(STRATEGIES) == MVP_STRATEGY_IDS
ENVELOPE = "INDEPENDENT_STRESS_BUDGET_ENVELOPE_NOT_JOINT_EVENT"
SCENARIO_FIELDS = {'scenario_id','version','strategies','category','model','severity','evidence_class','label','meaning','exposure_basis','assumptions'}
SCENARIO_ROUTES = {
    'NATIVE_STAKING_5PCT': ([NATIVE], 'STAKING_LOSS', 'EXPOSURE_TIMES_SEVERITY'),
    'GIMO_UNDERLYING_5PCT': ([GIMO], 'STAKING_LOSS', 'EXPOSURE_TIMES_SEVERITY'),
    'LP_WORST_ABSOLUTE': ([JAINE, OKU], 'LP_POSITION_VALUE', 'WORST_ABSOLUTE_LP_SHOCKS_V1'),
    'ASCEND_ECONOMIC_HAIRCUT': ([ASCEND], 'SOURCECORE_VALUE_LOSS', 'EXPOSURE_TIMES_SEVERITY'),
    'ASCEND_DEPENDENCIES_UNRESOLVED': ([ASCEND], 'DEPENDENCY_LOSS', 'EXPOSURE_TIMES_SEVERITY'),
}


class RiskError(ValueError):
    pass


@contextmanager
def precision():
    with localcontext() as ctx:
        ctx.prec = 60
        ctx.rounding = ROUND_HALF_EVEN
        yield


def decimal(value, *, fraction=False, positive=False):
    try:
        d = lp.number(value, positive=positive)
    except ValueError as exc:
        raise RiskError(str(exc)) from exc
    if d < 0 or (fraction and d > 1):
        raise RiskError('nonnegative value/fraction required')
    return d


def fingerprint(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def validate_scenario(s: dict) -> dict:
    if not isinstance(s, dict) or set(s) != SCENARIO_FIELDS:
        raise RiskError('scenario fields mismatch; no probability field')
    key = s['scenario_id'].removeprefix(SCENARIO_VERSION + ':') if isinstance(s['scenario_id'], str) else None
    if key not in SCENARIO_ROUTES or s['scenario_id'] != SCENARIO_VERSION + ':' + key or s['version'] != SCENARIO_VERSION:
        raise RiskError('unknown scenario/version')
    strategies, category, model = SCENARIO_ROUTES[key]
    if (s['strategies'], s['category'], s['model']) != (strategies, category, model):
        raise RiskError('causal scope/model mismatch')
    if s['label'] != LABEL or s['evidence_class'] not in {'MODELLED','MISSING'}:
        raise RiskError('synthetic scenario must remain modelled/missing')
    if any(not isinstance(s[k], str) or not s[k] for k in ('meaning','exposure_basis')) or not isinstance(s['assumptions'], list) or not s['assumptions'] or any(not isinstance(a, str) or not a for a in s['assumptions']):
        raise RiskError('provenance required')
    if key in {'NATIVE_STAKING_5PCT','GIMO_UNDERLYING_5PCT','ASCEND_ECONOMIC_HAIRCUT'}:
        if s['evidence_class'] != 'MODELLED' or decimal(s['severity'], fraction=True) != Decimal('.05'):
            raise RiskError('versioned severe/haircut benchmark must be 5%')
    elif s['severity'] is not None or s['evidence_class'] != ('MISSING' if key=='ASCEND_DEPENDENCIES_UNRESOLVED' else 'MODELLED'):
        raise RiskError('direct LP model/missing severity must not acquire a fabricated rate')
    return s


def load_scenarios(path=DEFAULT_DATA_DIR/'risk_scenarios.json') -> list[dict]:
    d=json.loads(Path(path).read_text())
    if set(d) != {'version','artifact_type','label','aggregation_rule','scenarios'} or d['version'] != SCENARIO_VERSION or d['artifact_type'] != lp.ARTIFACT_TYPE or d['label'] != LABEL or d['aggregation_rule'] != ENVELOPE:
        raise RiskError('unsupported synthetic scenario artifact')
    rows=[validate_scenario(s) for s in d['scenarios']]
    if len(rows)!=len(SCENARIO_ROUTES) or {s['scenario_id'] for s in rows} != {SCENARIO_VERSION+':'+k for k in SCENARIO_ROUTES}:
        raise RiskError('exact versioned scenario set required')
    return rows


@dataclass(frozen=True)
class StressResult:
    strategy_id: str
    scenario_id: str
    scenario_version: str
    scenario_fingerprint: str
    model_version: str
    risk_category: str
    exposure_basis: str
    allocation_value: str
    stressed_exposure_amount: str
    severity: str | None
    absolute_stressed_loss: str | None
    loss_fraction: str | None
    evidence_class: str
    stress_basis: str
    label: str
    risk_assessment_state: str
    aggregation_eligible: bool
    diagnostics: dict
    provenance: tuple[str, ...]
    reasons: tuple[str, ...]
    value_unit: str = 'MODELLED_USDC.e_VALUE_EQUIVALENT_USD'
    allocation_gate: str = 'NOT_EVALUATED_BY_RISK_MODEL'


def assess(strategy_id: str, scenario: dict, allocation_value: str, *, mode: str, lp_config: dict | None=None) -> StressResult:
    if mode != LABEL:
        raise RiskError('explicit synthetic mode required; no current risk evidence supplied')
    validate_scenario(scenario)
    if strategy_id not in STRATEGIES or strategy_id not in scenario['strategies']:
        raise RiskError('strategy/scenario scope mismatch')
    with precision():
        allocation=decimal(allocation_value)
        severity=scenario['severity']
        loss=None if severity is None else allocation*decimal(severity, fraction=True)
        state='UNRESOLVED' if scenario['evidence_class']=='MISSING' else 'ASSESSED_MODELLED'
        diag={}
        reasons=['Independent deterministic scenario; no probability/correlation claim',
                 'Does not establish return evidence, admission, executable quote, exit liquidity or deployment']
        if strategy_id==NATIVE:
            diag={'configured_validator_concentration':'UNRESOLVED','delegated_pending_split':'UNRESOLVED',
                  'exposure_assumption':'Entire synthetic allocation; no additional pending balance added'}
        elif strategy_id==GIMO:
            diag={'gimo_specific_protocol_severity':None,'gimo_protocol_risk':'UNRESOLVED',
                  'causal_losses_applied':1,'shared_severity_not_shared_event':True}
        elif strategy_id in lp.STRATEGIES:
            if lp_config is None or lp_config['strategy_id']!=strategy_id:
                raise RiskError('strategy-specific synthetic LP config required')
            lp.validate_config(lp_config)
            # A unit notional remains meaningful for zero allocation diagnostics.
            points=[lp.evaluate(lp_config,s,'1',mode=LABEL,expected_config_id=lp_config['config_id']) for s in lp.scenarios()]
            worst=max(points,key=lambda p: Decimal(p.absolute_lp_loss))  # stable scenario order breaks ties.
            fraction=decimal(worst.absolute_lp_loss,fraction=True)
            loss=allocation*fraction
            diag={'lp_absolute_stress_loss':lp.text(fraction),'worst_lp_scenario_id':worst.scenario_id,
                  'lp_config_id':lp_config['config_id'],'selection_rule':'WORST_ABSOLUTE_LOSS_ACROSS_LP_SHOCKS_V1',
                  'impermanent_loss_fraction':worst.impermanent_loss_fraction,'hodl_market_loss':worst.hodl_market_loss,
                  'lp_vs_hodl_difference_per_unit':worst.lp_vs_hodl_difference,'range_state':worst.range_state,
                  'shock_results_per_unit':[asdict(p) for p in points],
                  'only_absolute_loss_aggregated':True,'fees_execution_costs_included':False}
        elif strategy_id==ASCEND:
            state='PARTIALLY_ASSESSED' if loss is not None else 'UNRESOLVED'
            diag={'sourcecore_a0g_value':'Counted once','embedded_mellow_symbiotic':'Contained in a0G exposure; not additive',
                  'queue_funding_severity':None,'remote_dependency_severity':None,'oracle_accounting_severity':None,
                  'operator_data':'UNRESOLVED','allocation_gate':'CLOSED'}
            reasons.append('Ascend CLOSED; hypothetical analysis only, not allocatable')
        if loss is None:
            reasons.append('MISSING_SEVERITY_IS_NOT_ZERO')
        fraction=None if loss is None else (Decimal(0) if allocation==0 else loss/allocation)
        # At zero allocation, preserve the model fraction for budget diagnostics.
        if allocation==0 and loss is not None:
            fraction=decimal(diag['lp_absolute_stress_loss'],fraction=True) if strategy_id in lp.STRATEGIES else decimal(severity,fraction=True)
        return StressResult(strategy_id,scenario['scenario_id'],SCENARIO_VERSION,fingerprint(scenario),VERSION,
                            scenario['category'],scenario['exposure_basis'],lp.text(allocation),lp.text(allocation),severity,
                            None if loss is None else lp.text(loss),None if fraction is None else lp.text(fraction),
                            scenario['evidence_class'],'UNRESOLVED' if loss is None else 'MODELLED',LABEL,state,loss is not None,
                            diag,tuple(scenario['assumptions']),tuple(reasons),allocation_gate='CLOSED' if strategy_id==ASCEND else 'NOT_EVALUATED_BY_RISK_MODEL')


def aggregate(results: list[StressResult], weights: dict[str,str], decision_value: str, *, mode: str,
              allow_closed_analysis=False) -> dict:
    """Sum independent loss budgets, not a simultaneous causal-event prediction.

    Any positive unresolved exposure blocks the total; zero-weight unresolved
    records contribute exactly zero without pretending their severity is known.
    """
    if mode!=LABEL:
        raise RiskError('synthetic mode required')
    if set(weights)!=set(STRATEGIES) or len(results)!=5 or {r.strategy_id for r in results}!=set(STRATEGIES):
        raise RiskError('exactly five strategy results/weights required')
    with precision():
        total=decimal(decision_value,positive=True)
        w={s:decimal(v,fraction=True) for s,v in weights.items()}
        if sum(w.values())>1:
            raise RiskError('allocation weights exceed decision sleeve')
        rows=[];blocked=[]
        for r in results:
            if r.model_version!=VERSION or r.label!=LABEL or r.evidence_class not in {'MODELLED','MISSING'}:
                raise RiskError('incompatible/non-synthetic risk result')
            weight=w[r.strategy_id];expected=total*weight
            if decimal(r.allocation_value)!=expected or decimal(r.stressed_exposure_amount)>expected:
                raise RiskError('risk allocation identity mismatch')
            if weight>0 and r.strategy_id==ASCEND and not allow_closed_analysis:
                raise RiskError('Ascend CLOSED; explicit analysis-only override required')
            f=None if r.loss_fraction is None else decimal(r.loss_fraction,fraction=True)
            loss=None if r.absolute_stressed_loss is None else decimal(r.absolute_stressed_loss)
            if r.aggregation_eligible != (f is not None and loss is not None):
                raise RiskError('inconsistent risk qualification')
            if loss is not None and (loss>expected or loss!=expected*f):
                raise RiskError('inconsistent/invalid absolute loss')
            if weight==0:
                loss=Decimal(0);contribution=Decimal(0)
            elif not r.aggregation_eligible:
                blocked.append(r.strategy_id);loss=None;contribution=None
            else:
                contribution=weight*f
            rows.append({'strategy_id':r.strategy_id,'scenario_id':r.scenario_id,'weight':lp.text(weight),
                         'strategy_stress_loss_fraction':r.loss_fraction,'absolute_strategy_stress_loss':None if loss is None else lp.text(loss),
                         'weighted_contribution':None if contribution is None else lp.text(contribution),
                         'risk_category':r.risk_category,'risk_assessment_state':r.risk_assessment_state,
                         'allocation_gate':r.allocation_gate})
        def category_sum(category):
            subset=[r for r in rows if r['risk_category']==category]
            return None if any(r['weighted_contribution'] is None for r in subset) else lp.text(sum((Decimal(r['weighted_contribution']) for r in subset),Decimal(0)))
        return {'model_version':VERSION,'label':LABEL,'evidence_class':'MODELLED','aggregation_rule':ENVELOPE,
                'joint_event_assumed':False,'correlation':'UNRESOLVED_NOT_INFERRED','decision_value':decision_value,
                'idle_weight':lp.text(1-sum(w.values())),'rows':rows,'state':'UNRESOLVED' if blocked else 'ASSESSED_MODELLED',
                'unresolved_positive_allocations':blocked,
                'total_decision_sleeve_stress_loss':None if blocked else lp.text(sum(Decimal(r['absolute_strategy_stress_loss']) for r in rows)),
                'total_loss_fraction':None if blocked else lp.text(sum(Decimal(r['weighted_contribution']) for r in rows)),
                'lp_absolute_stress_loss':category_sum('LP_POSITION_VALUE'),
                'staking_stress_loss':category_sum('STAKING_LOSS'),
                'closed_gate_analysis_only':allow_closed_analysis,
                'limitations':['Sum of independent stress budgets is not a joint-event scenario or probability',
                               'Only named quantified components covered; unresolved dependency risks remain',
                               'Does not imply production admission or portfolio recommendation']}


def profile_constraints(budget: dict, profile: str, *, lp_absolute_limit: str | None=None) -> dict:
    """Explicit evaluation mapping. No implicit conversion of IL thresholds."""
    p=get_profile(profile)
    if budget.get('model_version')!=VERSION or budget.get('label')!=LABEL:
        raise RiskError('versioned synthetic budget required')
    with precision():
        max_weight=max(decimal(r['weight'],fraction=True) for r in budget['rows'])
        staking=budget['staking_stress_loss'];lp_loss=budget['lp_absolute_stress_loss']
        new_limit=None if lp_absolute_limit is None else decimal(lp_absolute_limit,fraction=True)
        def check(value,limit):
            return 'UNRESOLVED' if value is None else ('PASS' if decimal(value,fraction=True)<=limit else 'FAIL')
        return {'profile':p.name.value,'mode':LABEL,'optimizer_integration':'LEGACY_OPTIMIZERS_UNCHANGED',
                'max_strategy_concentration':{'limit':str(p.max_strategy_concentration),'result':check(lp.text(max_weight),Decimal(str(p.max_strategy_concentration)))},
                'max_slashing_stress_loss':{'limit':str(p.max_slashing_stress_loss),'meaning':'Weighted independent underlying-staking loss budget, not shared causal event','result':check(staking,Decimal(str(p.max_slashing_stress_loss)))},
                'max_decision_sleeve_lp_absolute_stress_loss':{'limit':lp_absolute_limit,'basis':'EXPLICIT_SYNTHETIC_USER_LIMIT' if new_limit is not None else 'UNRESOLVED_NO_NEW_PROFILE_DEFAULT',
                    'result':'UNRESOLVED' if new_limit is None else check(lp_loss,new_limit)},
                'max_portfolio_lp_il_stress':{'limit':str(p.max_portfolio_lp_il_stress),'result':'LEGACY_COMPATIBILITY_ONLY_NOT_APPLIED_TO_ABSOLUTE_LOSS'},
                'max_bridge_exposure':{'limit':str(p.max_bridge_exposure),'result':'UNRESOLVED_NO_BRIDGE_EXPOSURE_INPUT; REMOTE_DEPENDENCY_IS_NOT_USER_CAPITAL_BRIDGE'},
                'max_exit_time_days':{'limit':str(p.max_exit_time_days),'result':'LEGACY_ONLY; NEW_EXIT_PRIMITIVE_NOT_RANKING_OR_DEADLINE_INPUT'},
                'overall_risk_clearance':'NOT_ESTABLISHED'}
