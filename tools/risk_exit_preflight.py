"""Read-only deterministic stress/exit replay; no RPC, randomness or wall clock."""
from dataclasses import asdict
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.ascend_optimizer import risk_stress as r, exit_liquidity as e, lp_range_stress as lp


def record(result):
    # Return JSON-native lists rather than dataclass tuple fields.
    return json.loads(json.dumps(asdict(result), allow_nan=False))


def risk_replay():
    scenarios=r.load_scenarios();configs={c['strategy_id']:c for c in lp.load_configs()}
    rows=[r.assess(sid,s,'1000',mode=r.LABEL,lp_config=configs.get(sid)) for s in scenarios for sid in s['strategies']]
    # Five equal, hypothetical allocations, including CLOSED Ascend only through
    # an explicit analysis override. This is never a recommendation fixture.
    allocations=[x for x in rows if x.aggregation_eligible]
    budget=r.aggregate(allocations,{s:'0.2' for s in r.STRATEGIES},'5000',mode=r.LABEL,allow_closed_analysis=True)
    return {'model_version':r.VERSION,'scenario_version':r.SCENARIO_VERSION,'label':r.LABEL,'evidence_class':'MODELLED',
            'scenario_artifact_fingerprint':r.fingerprint(scenarios),'scenarios':scenarios,
            'notional_basis':'Each hypothetical strategy allocation=1000 modelled USD-equivalent; decision sleeve=5000',
            'strategy_results':[record(x) for x in rows],'decision_sleeve_budget':budget,
            'profile_constraint_mapping':[r.profile_constraints(budget,p) for p in ('Conservative','Balanced','Aggressive')],
            'explicit_lp_limit_example':r.profile_constraints(budget,'Balanced',lp_absolute_limit='0.10'),
            'public_deployment_performed':False,'public_deployment_required':False,
            'limitations':['Independent budget envelope, not a simultaneous Native/Gimo/Ascend slash',
                           'Incomplete dependency risks; overall risk clearance not established',
                           'Legacy optimizer thresholds remain in use; new LP threshold defaults are deliberately unresolved']}


def exit_replay():
    configs=e.load_configs()
    return {'model_version':e.VERSION,'config_version':e.CONFIG_VERSION,'label':r.LABEL,
            'evidence_class':'MODELLED','configurations':configs,
            'production_source_path_only':[record(e.assess(s)) for s in r.STRATEGIES],
            'synthetic_exit_results':[record(e.assess(c['strategy_id'],mode=r.LABEL,config=c,holding_horizon_days='90')) for c in configs],
            'cash_deadline_optimization_implemented':False,'public_deployment_performed':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind',choices=['risk','exit'],required=True)
    parser.add_argument('--check',type=Path)
    args=parser.parse_args();result=risk_replay() if args.kind=='risk' else exit_replay()
    if args.check:
        if json.loads(args.check.read_text())!=result:
            raise SystemExit('Replay differs from committed artifact')
        print(args.kind+': SYNTHETIC_EVALUATION_ONLY replay matches exactly')
    else:
        print(json.dumps(result,indent=2,allow_nan=False))
