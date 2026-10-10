"""Focused synthetic policy validation replay, not the final experiment harness."""
import argparse
import json
from pathlib import Path
import runpy
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.ascend_optimizer import evaluation_policy as p, risk_stress as r
from tools.economics_preflight import repository_baseline
ROOT=Path(__file__).resolve().parents[1]


def replay():
    t=runpy.run_path(str(ROOT/'tests/test_evaluation_policy.py'))
    examples=[]
    for name,kw in [
        ('lp_conservative',{'profile':'Conservative','sids':(r.JAINE,)}),
        ('lp_balanced',{'profile':'Balanced','sids':(r.JAINE,)}),
        ('lp_aggressive',{'profile':'Aggressive','sids':(r.JAINE,)}),
        ('async_tight_deadline',{'deadline':'1'}),
        ('async_relaxed_deadline',{'deadline':'8'}),
        ('profit_ranking',{'sids':(r.NATIVE,r.JAINE),'returns':{r.NATIVE:'0.2',r.JAINE:'0.1'}})]:
        q=t['synthetic_run'](**kw);d=q.to_dict()
        examples.append({'case':name,'profile':q.profile,'grid':list(q.grid),'recommendation':d['recommendation'],
                         'selected_policy':q.evaluation_policy,'revalidation':q.revalidation,
                         'positive_economic_points':[{'strategy_id':c.strategy_id,'weight':c.weight,'amount_0g':c.amount_0g,
                             'net_profit_usd':c.net_profit_usd,'fixed_cost_usd':c.fixed_execution_cost_usd}
                             for c in q.candidates if c.weight>0 and c.eligible]})
    return json.loads(json.dumps({'policy_version':p.VERSION,'scope':p.SCOPE,'label':p.LABEL,'evidence_class':'MODELLED',
        'policy':p.load_policy(),'feasibility_examples':t['example_results'](),'amount_aware_examples':examples,
        'production_baseline':repository_baseline(),'whole_portfolio_compliance':'NOT_ASSESSED',
        'final_experiment_harness_started':False,'public_deployment_performed':False,
        'limitations':['Focused validation scenarios, not benchmark comparisons or calibrated risk limits',
                       'Legacy optimizer remains compatibility-only; new policy requires explicit synthetic economics',
                       'No existing holdings or prior exits inferred; only designated decision capital is allocated']},allow_nan=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',type=Path)
    args=parser.parse_args();result=replay()
    if args.check:
        if json.loads(args.check.read_text())!=result:raise SystemExit('Policy replay differs from committed artifact')
        print('SYNTHETIC_EVALUATION_ONLY: 10 feasibility examples / 6 focused search examples replay exactly')
    else:print(json.dumps(result,indent=2,allow_nan=False))
