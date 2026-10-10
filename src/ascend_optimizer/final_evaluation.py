"""FINAL_EVALUATION_V1: deterministic synthetic four-method comparison only."""
from collections import Counter
from dataclasses import asdict
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from pathlib import Path
from statistics import mean, median
import csv
import io
import json

import pandas as pd
from . import evaluation_policy as policy, risk_stress as risk, lp_range_stress as lp
from .economics_evidence import EconomicsError
from .amount_optimizer import run_amount_optimizer, candidate_grid
from .optimizer import optimize_portfolio
from .lp_execution import MODELLED_LP_STRESS_20PCT
from .profiles import get_profile
from .evaluation_baselines import METHODS, allocate
from .final_evaluation_inputs import SyntheticInputs

ROOT = Path(__file__).resolve().parents[2]
VERSION = 'FINAL_EVALUATION_V1'
SCENARIOS = 'FINAL_EVALUATION_SCENARIOS_V1'
LABEL = policy.LABEL
CONFIG = ROOT/'data/final_evaluation_config.json'
PROFILES = ('Conservative', 'Balanced', 'Aggressive')
TARGET_IDS = {*(f'DEADLINE_{regime}_{d}' for regime in ('STAKING','LP') for d in ('1','8','15')),
    'FIXED_100','FIXED_1000','FIXED_10000','FIXED_ZERO_CONTROL',
    *(f'LP_PROGRESSION_{p.upper()}' for p in PROFILES), 'QUOTE_CURVE','QUOTE_CONSTANT_CONTROL',
    'NEGATIVE','MISSING_RETURN','MISSING_COST','QUOTE_MISMATCH','ADMISSION_FAILURE','ASCEND_ATTRACTIVE','TIE'}


def fmt(value):
    """Presentation boundary only: 12 decimal places, no legacy float dust."""
    if value is None or isinstance(value, (str, bool)):
        return value
    d = Decimal(str(value))
    if not d.is_finite():
        raise ValueError('nonfinite benchmark output')
    with localcontext() as ctx:
        ctx.prec = 60
        d = d.quantize(Decimal('0.000000000001'), rounding=ROUND_HALF_EVEN)
    return format(d.normalize(), 'f') if d else '0'


def presentation(value):
    if isinstance(value, dict):
        return {k:presentation(v) for k,v in value.items()}
    if isinstance(value, (list, tuple)):
        return [presentation(v) for v in value]
    if isinstance(value, (float, Decimal)):
        return fmt(value)
    return value


def load_config(path=CONFIG):
    q = json.loads(Path(path).read_text())
    if (q['version'] != VERSION or q['scenario_version'] != SCENARIOS or tuple(q['methods']) != METHODS
        or q['label'] != LABEL or q['scope'] != 'DECISION_SLEEVE'
        or q['whole_portfolio_compliance'] != 'NOT_ASSESSED' or q['ascend_gate'] != 'CLOSED'):
        raise ValueError('frozen synthetic evaluation contract required')
    if Decimal(q['package']['legacy_lp_proxy']) != Decimal(str(MODELLED_LP_STRESS_20PCT)):
        raise ValueError('legacy proxy must match frozen implementation')
    expected = {f'CORE_{p.upper()}_{a}_{h}' for p in PROFILES for a in ('100','1000','10000') for h in ('30','90','365')}
    rows = q['scenarios']; ids = [s['scenario_id'] for s in rows]
    if (len(set(ids)) != len(ids) or {s['scenario_id'] for s in rows if s['kind']=='CORE'} != expected
        or {s['scenario_id'] for s in rows if s['kind']=='TARGETED'} != TARGET_IDS or len(rows)!=49):
        raise ValueError('unique scenario IDs and exact core matrix required')
    for s in rows:
        if s['version'] != SCENARIOS or s['label'] != LABEL or s['profile'] not in PROFILES:
            raise ValueError('invalid scenario identity or evidence label')
        if any(not Decimal(s[k]).is_finite() for k in ('decision_amount_0g','holding_horizon_days')):
            raise ValueError('finite scenario inputs required')
        changes=s['modified_assumptions']
        if set(changes)-{'returns','fixed_costs','quote_base','quote_slope','missing_returns','missing_costs','quote_mismatch','admission_rejected'}:
            raise ValueError('unsupported scenario assumption modification')
        for k in ('returns','fixed_costs'):
            for sid,v in changes.get(k,{}).items():
                if sid not in risk.STRATEGIES or not Decimal(v).is_finite() or Decimal(v)<(0 if k=='fixed_costs' else -1):
                    raise ValueError('invalid economic assumption')
        for k in ('missing_returns','missing_costs','quote_mismatch','admission_rejected'):
            if set(changes.get(k,[]))-set(risk.STRATEGIES):raise ValueError('unknown assumption strategy')
        if Decimal(s['decision_amount_0g']) <= 0 or Decimal(s['holding_horizon_days']) <= 0:
            raise ValueError('invalid amount/horizon')
        if s['cash_deadline_days'] is not None and Decimal(s['cash_deadline_days']) < 0:
            raise ValueError('invalid deadline')
        if s['kind']=='CORE' and (s['cash_deadline_days'] is not None or s['modified_assumptions']):
            raise ValueError('core is the unchanged no-deadline package')
    return q


class TrackingPolicy:
    """Observe final-policy candidate exclusion states without changing search."""
    def __init__(self):
        self.inner = policy.PolicyEvaluator()
        self.failures = Counter()
        self.calls = Counter()

    def prepare(self, **context):
        session = self.inner.prepare(**context)
        stage = context['stage']
        def checked(**kwargs):
            result = session(**kwargs)
            self.calls[stage] += 1
            if stage == 'CANDIDATE' and result.overall != 'PASS':
                for name, check in result.constraints.items():
                    if check['state'] in ('FAIL','UNRESOLVED','INCOMPATIBLE_MODELLED'):
                        self.failures[name] += 1
            return result
        return checked


def legacy_candidates(inputs):
    """Reference-full-notional economics -> frozen linear coefficients.

    The existing solver scales that coefficient by weight, including reference
    fixed cost and quote effects. This adapter never adds final risk/deadlines.
    """
    scenario = inputs.scenario
    value = Decimal(scenario['decision_amount_0g'])*Decimal(inputs.package['price_usd'])
    rates, rejection = inputs.apparent_returns()
    exits = {s:policy.exits.assess(s, mode=LABEL, config=c) for s,c in policy.PolicyEvaluator().exit_configs.items()}
    rows = []
    for sid in risk.STRATEGIES:
        reason = list(rejection.get(sid, []))
        point = None
        if not reason:
            try:
                point = inputs.point(sid, scenario['decision_amount_0g'])
            except EconomicsError as exc:
                reason.append(str(exc))
        rows.append(dict(strategy_id=sid, net_return_horizon=None if point is None else point.net_return_horizon,
            optimizer_eligible=not reason, eligibility_reasons='|'.join(reason), liquidity_usd=float(value), bridge_fraction=0,
            lp_stress_loss_20pct=float(inputs.package['legacy_lp_proxy']) if sid in lp.STRATEGIES else 0,
            exit_time_days=float(exits[sid].time_to_cash_days), slashing_stress_loss=.05 if sid in (risk.NATIVE,risk.GIMO) else 0,
            max_entry_exit_slippage=0 if point is None else max(point.entry_slippage_rate,point.exit_slippage_rate)))
    return pd.DataFrame(rows)


def score_allocation(inputs, weights):
    """Common exact-allocation rescore, not a baseline selection capability."""
    totals = dict(gross=Decimal(0), profit=Decimal(0), lifecycle=Decimal(0), fixed=Decimal(0), quote=Decimal(0))
    points, errors = [], []
    for sid, weight in weights.items():
        if weight == 0:
            continue
        amount = Decimal(inputs.scenario['decision_amount_0g'])*weight
        try:
            point = inputs.point(sid, amount)
            ev = point.evidence
            for key, val in [('gross',ev['return']['expected_gross_income_usd']),('profit',point.net_profit_usd),
                ('lifecycle',ev['costs']['total_cost_usd']),('fixed',point.fixed_cost_usd),('quote',ev['quote_cost_usd'])]:
                totals[key] += Decimal(str(val))
            points.append(dict(strategy_id=sid, amount_0g=str(amount), net_profit_usd=point.net_profit_usd,
                fixed_cost_usd=point.fixed_cost_usd, quote_loss_usd=ev['quote_cost_usd'],
                return_evidence_ids=[r['evidence_id'] for r in ev['return']['provenance']],
                quote_ids=[q['quote_id'] for q in ev['quotes']]))
        except EconomicsError as exc:
            errors.append(sid+':'+str(exc))
    return totals if not errors else None, points, errors


def normalize(config, scenario, method):
    inputs = SyntheticInputs(config, scenario)
    amount = Decimal(scenario['decision_amount_0g']); value = amount*Decimal(inputs.package['price_usd'])
    profile = get_profile(scenario['profile'])
    diagnostics = {}; reasons = {}; reported_profit = 'NOT_SUPPORTED'
    if method in METHODS[:2]:
        rates, reasons = inputs.apparent_returns()
        weights, idle = allocate(method, rates, profile.max_strategy_concentration, risk.STRATEGIES)
        diagnostics = {'selection_rule':'RANKED_CAP_FILL' if method==METHODS[0] else 'EQUAL_TARGET_CAPPED_NO_REDISTRIBUTION',
            'ranking_apparent_net_protocol_apy':rates, 'eligibility_reasons':reasons}
    elif method == METHODS[2]:
        table = legacy_candidates(inputs)
        result = optimize_portfolio(table, portfolio_value_usd=float(value), profile=profile)
        weights = {s:Decimal(fmt(result.allocations.get(s,0))) for s in risk.STRATEGIES}
        idle = 1-sum(weights.values())
        reported_profit = fmt(result.expected_net_profit_usd)
        reasons = result.excluded_strategies
        diagnostics = {'implementation':'ascend_optimizer.optimizer.optimize_portfolio', 'reference_coefficients':table.astype(object).where(pd.notna(table), None).to_dict('records'),
            'excluded_strategies':reasons, 'legacy_lp_il_budget':result.portfolio_lp_il_stress,
            'legacy_slashing_budget':result.portfolio_slashing_stress_loss,'solver_status':result.solver_status}
    else:
        tracker = TrackingPolicy()
        result = run_amount_optimizer(inputs.strategies, inputs.snapshots, decision_amount=float(amount),
            price_usd=float(inputs.package['price_usd']), horizon_days=float(scenario['holding_horizon_days']),
            profile=profile, as_of=inputs.as_of, admission_fn=inputs.admission,
            economics_fn=inputs.economics, economics_mode=LABEL, evaluation_policy_mode=LABEL,
            evaluation_policy_fn=tracker, cash_deadline_days=scenario['cash_deadline_days'])
        if result.revalidation == 'FAILED':
            raise ValueError('benchmark selected revalidation failed: '+str(result.revalidation_errors))
        weights = {s:Decimal(str(next((c.weight for c in result.selected if c.strategy_id==s),0))) for s in risk.STRATEGIES}
        idle = 1-sum(weights.values())
        reported_profit = fmt(sum(c.net_profit_usd for c in result.selected))
        reasons = {s:sorted({reason for c in result.candidates if c.strategy_id==s for reason in c.rejection_reasons}) for s in risk.STRATEGIES}
        diagnostics = {'implementation':'ascend_optimizer.amount_optimizer.run_amount_optimizer',
            'grid':result.grid,'tested_combinations':result.combinations_tested,
            'selected_revalidation':result.revalidation, 'policy_revalidation_calls':tracker.calls['REVALIDATION'],
            'candidate_policy_exclusions':dict(tracker.failures), 'point_rejections':reasons,
            'selected_policy':result.evaluation_policy}
    # Solver formatting boundary: quantize weights, then derive residual idle
    # exactly, rather than independently rounding six fields.
    weights = {s:Decimal(fmt(w)) for s,w in weights.items()}
    idle = 1-sum(weights.values())
    if weights[risk.ASCEND] != 0 or sum(weights.values())+idle != 1 or idle < 0:
        raise ValueError('invalid recommendation sleeve or closed gate breach')
    # Common policy diagnostics for all methods do not retrofit its constraints.
    session = policy.PolicyEvaluator().prepare(profile=scenario['profile'], decision_amount_0g=str(amount),
        decision_value=str(value), holding_horizon_days=scenario['holding_horizon_days'],
        cash_deadline_days=scenario['cash_deadline_days'], stage='POSTHOC_DIAGNOSTIC')
    assessed = session(weights={s:str(w) for s,w in weights.items()},idle_weight=str(idle))
    totals, points, errors = score_allocation(inputs,weights)
    net = 'NOT_ASSESSED' if totals is None else totals['profit']/value
    annual = 'NOT_ASSESSED' if totals is None or net <= -1 else (Decimal(1)+net)**(Decimal(365)/Decimal(scenario['holding_horizon_days']))-1
    support = config['capabilities'][method]
    enforced_deadline = assessed.constraints['cash_deadline']['state'] if method==METHODS[3] else 'NOT_SUPPORTED'
    budget = assessed.risk_budget
    return presentation(dict(evaluation_version=VERSION, scenario_id=scenario['scenario_id'], scenario_version=SCENARIOS,
        method_id=method, profile=scenario['profile'], scope='DECISION_SLEEVE', decision_amount_0g=str(amount),
        valuation=inputs.valuation, holding_horizon_days=scenario['holding_horizon_days'], cash_deadline_days=scenario['cash_deadline_days'],
        allocation_weights=weights, idle_weight=idle, expected_gross_return='NOT_ASSESSED' if totals is None else totals['gross'],
        expected_net_profit='NOT_ASSESSED' if totals is None else totals['profit'],expected_net_return=net, net_apy=annual,
        lifecycle_cost='NOT_ASSESSED' if totals is None else totals['lifecycle'], fixed_cost='NOT_ASSESSED' if totals is None else totals['fixed'],
        lp_quote_execution_loss='NOT_ASSESSED' if totals is None else totals['quote'],
        profit_basis='COMMON_EXACT_ALLOCATION_RESCORE_NOT_METHOD_SELECTION_OBJECTIVE',
        method_reported_profit=reported_profit,
        selection_profit_comparability=('LIMITED_REFERENCE_LINEARIZATION' if method==METHODS[2] else
            'NOT_SUPPORTED' if method in METHODS[:2] else 'EXACT_CANDIDATE_ECONOMICS'),
        method_lifecycle_cost=totals['lifecycle'] if method==METHODS[3] and totals is not None else 'NOT_SUPPORTED_EXACT_ALLOCATION',
        method_lp_quote_loss=totals['quote'] if method==METHODS[3] and totals is not None else 'NOT_SUPPORTED_EXACT_ALLOCATION',
        enforced_constraint_set=[k for k,v in support.items() if v in ('SUPPORTED','LEGACY_ONLY','APPROXIMATED')], profit_comparability='DIRECT_COMMON_RESCORE' if totals is not None else 'LIMITED',
        staking_stress=budget['staking_stress_loss'], lp_absolute_stress=budget['lp_absolute_stress_loss'],
        total_stress_budget=budget['total_loss_fraction'], stress_basis='POSTHOC_RISK_STRESS_V1_INDEPENDENT_BUDGET_NOT_JOINT_EVENT',
        deadline_compatibility=enforced_deadline, posthoc_deadline_compatibility=assessed.constraints['cash_deadline']['state'],
        feasibility_state='PASS_METHOD_SUPPORTED_CONSTRAINTS', final_policy_feasibility=assessed.overall,
        final_policy_enforced=method==METHODS[3],recommendation_state='IDLE_ALLOWED' if idle==1 else 'SYNTHETIC_RECOMMENDATION',
        binding_constraints=assessed.binding_constraints if method==METHODS[3] else ['NOT_ASSESSED_FINAL_POLICY_NOT_ENFORCED'],
        posthoc_policy_constraints=assessed.constraints, rejection_reasons=reasons, common_rescore_errors=errors,
        supported_feature_flags=support,evidence_mode=LABEL,whole_portfolio_compliance='NOT_ASSESSED',
        execution_readiness='NOT_ESTABLISHED', public_live_proof_state='NOT_ESTABLISHED',
        diagnostics=diagnostics, common_economic_points=points))


def summary(config, rows):
    by = {(r['scenario_id'],r['method_id']):r for r in rows}
    disagreement=[]; deltas=[]; drivers=Counter(); method_counts={}
    for m in METHODS:
        rs=[r for r in rows if r['method_id']==m]
        method_counts[m]={'rows':len(rs),'recommendation_rows':sum(r['idle_weight']!='1' for r in rs),'idle_rows':sum(r['idle_weight']=='1' for r in rs)}
    any_difference=0; abstains=0; invests=0
    for s in config['scenarios']:
        rs=[by[(s['scenario_id'],m)] for m in METHODS]
        if len({json.dumps(r['allocation_weights'],sort_keys=True) for r in rs})>1:any_difference+=1
        a,b=rs[3],rs[2]
        abstains += a['idle_weight']=='1' and any(r['idle_weight']!='1' for r in rs[:3])
        invests += a['idle_weight']!='1' and any(r['idle_weight']=='1' for r in rs[:3])
        if a['allocation_weights'] != b['allocation_weights']:
            contributors=[]
            fail={k:1 for k,v in b['posthoc_policy_constraints'].items() if v['state'] in ('FAIL','UNRESOLVED','INCOMPATIBLE_MODELLED')}
            for key,driver in [('lp_absolute_stress','LP_ABSOLUTE_STRESS'),('staking_stress','STAKING_STRESS'),('cash_deadline','CASH_DEADLINE')]:
                if fail.get(key):contributors.append(driver)
            reason_text=json.dumps(a['rejection_reasons'])
            if 'admission' in reason_text.lower():contributors.append('ADMISSION')
            if 'MISSING' in reason_text or 'AMBIGUOUS' in reason_text:contributors.append('MISSING_EVIDENCE')
            if any(r['fixed_cost']!='NOT_ASSESSED' and Decimal(r['fixed_cost'])>0 for r in (a,b)):
                contributors.append('FIXED_COST')
            if inputs_quote_varies(config,s) and any(Decimal(r['allocation_weights'][sid])>0 for r in (a,b) for sid in lp.STRATEGIES):contributors.append('AMOUNT_SPECIFIC_QUOTE')
            if any(Decimal(w)*10 != (Decimal(w)*10).to_integral_value() for w in b['allocation_weights'].values()):contributors.append('GRID_DISCRETIZATION')
            if not contributors:contributors=['OBJECTIVE_DIFFERENCE']
            primary=contributors[0] if len(contributors)==1 else 'MULTIPLE'
            drivers[primary]+=1
            comparable=a['profit_comparability']==b['profit_comparability']=='DIRECT_COMMON_RESCORE'
            delta=Decimal(a['expected_net_profit'])-Decimal(b['expected_net_profit']) if comparable else None
            disagreement.append({'scenario_id':s['scenario_id'],'primary_driver':primary,'diagnostic_contributors':contributors,
                'attribution_basis':'DIAGNOSTIC_ASSOCIATION_NOT_ISOLATED_CAUSAL_EFFECT',
                'driver_detail':'SECONDARY_TIE_SELECTION_NOT_PROFIT_FORMULA' if primary=='OBJECTIVE_DIFFERENCE' and delta==0 else 'SUPPORTED_DIAGNOSTIC_CONTRIBUTORS',
                'profit_comparability':'DIRECT_COMMON_RESCORE' if comparable else 'LIMITED',
                'common_profit_delta':delta})
        if a['profit_comparability']==b['profit_comparability']=='DIRECT_COMMON_RESCORE':
            deltas.append(Decimal(a['expected_net_profit'])-Decimal(b['expected_net_profit']))
    constraints=Counter();deadline_exclusions=Counter(); blocking=Counter()
    for row in rows:
        if row['method_id']!=METHODS[3]:continue
        constraints.update(k for k,v in row['diagnostics']['candidate_policy_exclusions'].items() if v)
        constraints.update(k for k in row['binding_constraints'] if k not in row['diagnostics']['candidate_policy_exclusions'])
        if row['rejection_reasons'].get(risk.ASCEND):blocking['gate']+=1
        if any(reasons for sid,reasons in row['rejection_reasons'].items() if sid!=risk.ASCEND):blocking['admission_or_evidence']+=1
        if row['cash_deadline_days'] is not None:
            for sid,compat in row['diagnostics']['selected_policy']['per_strategy_exit_compatibility'].items():
                # Selected zero states don't report exclusion; use unchanged exit configs for all potential strategies.
                if sid not in (risk.NATIVE,risk.GIMO):continue
                exit_=policy.PolicyEvaluator().exit_configs[sid]
                days=policy.exits.assess(sid,mode=LABEL,config=exit_).time_to_cash_days
                if Decimal(days)>Decimal(row['cash_deadline_days']):deadline_exclusions[sid]+=1
    def changed(a,b):return by[(a,METHODS[3])]['allocation_weights']!=by[(b,METHODS[3])]['allocation_weights']
    return presentation(dict(evaluation_version=VERSION,label=LABEL,total_scenarios=len(config['scenarios']),
        normalized_rows=len(rows),core_scenarios=27,core_rows=108,targeted_scenarios=len(config['scenarios'])-27,
        method_counts=method_counts,method_disagreement_count=any_difference,amount_vs_legacy_allocation_difference_count=len(disagreement),
        amount_vs_legacy_profit_comparison_count=len(deltas),mean_comparable_profit_delta=mean(deltas),median_comparable_profit_delta=median(deltas),
        limited_profit_rows=sum(r['profit_comparability']=='LIMITED' for r in rows),
        method_selection_profit_comparability='LIMITED_LEGACY_REFERENCE_LINEARIZATION_VS_EXACT_COST_QUOTE_OBJECTIVE',
        difference_driver_counts=dict(drivers),disagreements=disagreement,
        amount_candidate_exclusion_or_selected_binding_scenario_counts=dict(constraints),
        amount_gate_or_admission_evidence_block_counts=dict(blocking),
        fixed_cost_changes_decision_count=int(changed('FIXED_100','FIXED_ZERO_CONTROL')),
        quote_effect_changes_decision_count=int(changed('QUOTE_CURVE','QUOTE_CONSTANT_CONTROL')),
        sensitivity_count_basis='Explicit paired ablations only; other diagnostic associations are not causal counts',
        deadline_driven_strategy_exclusions=dict(deadline_exclusions),amount_abstains_other_allocates=abstains,
        amount_invests_other_idles=invests,statistics_basis='Descriptive deterministic counts over this synthetic matrix, not market frequencies'))


def inputs_quote_varies(config,scenario):
    return Decimal(scenario['modified_assumptions'].get('quote_slope',config['package']['quote_slope']))!=0


def replay(config=None):
    config = load_config() if config is None else config
    with localcontext() as ctx:
        ctx.prec=60;ctx.rounding=ROUND_HALF_EVEN
        rows=[normalize(config,s,m) for s in config['scenarios'] for m in METHODS]
        from tools.economics_preflight import repository_baseline
        raw=dict(evaluation_version=VERSION,scenario_version=SCENARIOS,label=LABEL,scope='DECISION_SLEEVE',
            input_fingerprint=risk.fingerprint(config), dependency_fingerprints={path:risk.fingerprint(json.loads((ROOT/path).read_text()))
                for path in ('data/evaluation_policy.json','data/risk_scenarios.json','data/lp_evaluation_config.json','data/exit_evaluation_config.json')},
            synthetic_config=config,production_baseline=repository_baseline(),rows=rows)
        return raw,summary(config,rows)


def json_bytes(value):
    return (json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n').encode()


def csv_bytes(rows):
    out=io.StringIO(newline='');fields=['evaluation_version','scenario_version','scope','price_usd','scenario_id','method_id','profile','decision_amount_0g','holding_horizon_days','cash_deadline_days',
        *risk.STRATEGIES,'idle_weight','expected_gross_return','expected_net_profit','expected_net_return','net_apy','lifecycle_cost','fixed_cost',
        'lp_quote_execution_loss','staking_stress','lp_absolute_stress','total_stress_budget','deadline_compatibility','final_policy_feasibility',
        'final_policy_enforced','recommendation_state','profit_comparability','evidence_mode','whole_portfolio_compliance','execution_readiness','public_live_proof_state','method_reported_profit','selection_profit_comparability','method_lifecycle_cost','method_lp_quote_loss',
        'binding_constraints','rejection_reasons','supported_feature_flags']
    writer=csv.DictWriter(out,fieldnames=fields,lineterminator='\n');writer.writeheader()
    for row in rows:
        flat={k:row.get(k) for k in fields};flat.update(row['allocation_weights']);flat['cash_deadline_days']=row['cash_deadline_days'] or 'NONE'
        flat['price_usd']=row['valuation']['price_usd']
        for key in ('binding_constraints','rejection_reasons','supported_feature_flags'):
            flat[key]=json.dumps(row[key],sort_keys=True,separators=(',',':'))
        writer.writerow(flat)
    return out.getvalue().encode()
