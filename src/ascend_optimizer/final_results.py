"""FINAL_RESULTS_V1: presentation of hash-pinned Iteration 23 outputs only.

No optimizer execution, network, observations, wall clock, or new assumptions.
"""
from collections import Counter
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from hashlib import sha256
from pathlib import Path
import csv
import io
import json

from .final_evaluation import fmt
from .evaluation_baselines import METHODS
from .risk_stress import STRATEGIES, ASCEND, NATIVE, GIMO, JAINE, OKU

ROOT = Path(__file__).resolve().parents[2]
VERSION = 'FINAL_RESULTS_V1'
FINDINGS_VERSION = 'CAPSTONE_FINDINGS_V1'
LABEL = 'SYNTHETIC_EVALUATION_ONLY'
SOURCE_HEAD = '7abfa1a347f35985052bee617e1bd82165f471f0'
SOURCE_HASHES = {
    'results/final_evaluation_iteration23.json':'746d2e77b19c5f701e6171902b4902f414c6ad4098691fdb493abd1ab60c08ee',
    'results/final_evaluation_iteration23.csv':'cee106705b5622766c0080a64d8318e83c83ca7b36a3dc8a6c0618b6a6f9f75d',
    'results/final_evaluation_iteration23_summary.json':'215f2d17a1af41ffc112395333c8a298110771532c389b3c06b22be420523da0',
    'data/final_evaluation_config.json':'8c66ed55132aa271e422d660b1684f36d25b592256e771c14c4cd6af0e9ec941',
    'data/final_evaluation_contract.md':'54127489a6b03b58aa9bbfbed91786c8d8ea217e17e7a9c2af4caba78d1cdb8c',
}
METHOD_LABELS = dict(zip(METHODS, ('Highest Yield','Equal Weight','Legacy Linear','Policy-Aware Amount')))
ASSET_LABELS = dict(zip(STRATEGIES, ('Native','Gimo','Jaine','Oku','Ascend')))
REPRESENTATIVES = ('FIXED_100','FIXED_1000','FIXED_ZERO_CONTROL','QUOTE_CURVE','QUOTE_CONSTANT_CONTROL',
    'LP_PROGRESSION_CONSERVATIVE','LP_PROGRESSION_BALANCED','LP_PROGRESSION_AGGRESSIVE',
    'DEADLINE_STAKING_1','DEADLINE_STAKING_8','DEADLINE_STAKING_15','NEGATIVE','MISSING_COST','ASCEND_ATTRACTIVE','TIE')
DIAGNOSTIC_NAMES = {'lp_absolute_stress':'LP absolute stress','concentration':'Concentration',
                    'staking_stress':'Staking stress','cash_deadline':'Cash deadline'}
MATRIX_NOTE = 'Percentages describe the defined deterministic scenario matrix, not empirical market probabilities.'
DIAGNOSTIC_NOTE = ('These are scenarios in which the constraint excluded candidate allocations or appeared as a selected binding constraint. '
    'They are not empirical frequencies, probabilities, or mutually exclusive counts.')


class SourceIntegrityError(ValueError):
    pass


def require(condition, message):
    if not condition:raise SourceIntegrityError(message)


def read_sources(root=ROOT):
    root=Path(root)
    for path,expected in SOURCE_HASHES.items():
        require(sha256((root/path).read_bytes()).hexdigest()==expected,'Frozen source hash mismatch: '+path)
    raw=json.loads((root/'results/final_evaluation_iteration23.json').read_text())
    summary=json.loads((root/'results/final_evaluation_iteration23_summary.json').read_text())
    config=json.loads((root/'data/final_evaluation_config.json').read_text())
    validate(raw,summary,config)
    flat=list(csv.DictReader(io.StringIO((root/'results/final_evaluation_iteration23.csv').read_text())))
    require(len(flat)==196,'CSV row count')
    for source,row in zip(raw['rows'],flat,strict=True):
        require((source['scenario_id'],source['method_id'])==(row['scenario_id'],row['method_id']),'CSV row identity')
        require(all(source['allocation_weights'][sid]==row[sid] for sid in STRATEGIES),'CSV allocation mismatch')
    return raw,summary,config


def validate(raw,summary,config):
    require(raw['evaluation_version']==summary['evaluation_version']==config['version']=='FINAL_EVALUATION_V1','Evaluation version')
    require(raw['label']==summary['label']==config['label']==LABEL,'Synthetic evidence label')
    rows=raw['rows'];scenarios=config['scenarios']
    require(len(scenarios)==49 and len(rows)==196,'Scenario/row count')
    require(tuple(config['methods'])==METHODS and {r['method_id'] for r in rows}==set(METHODS),'Exactly four methods')
    require(len({(r['scenario_id'],r['method_id']) for r in rows})==196,'Duplicate result row')
    require({r['scenario_id'] for r in rows}=={s['scenario_id'] for s in scenarios},'Scenario membership')
    core={s['scenario_id'] for s in scenarios if s['kind']=='CORE'}
    require(len(core)==27 and sum(r['scenario_id'] in core for r in rows)==108,'Core matrix')
    require(sum(s['kind']=='TARGETED' for s in scenarios)==22,'Targeted matrix')
    expected={'total_scenarios':49,'normalized_rows':196,'core_scenarios':27,'core_rows':108,'targeted_scenarios':22,
              'amount_vs_legacy_allocation_difference_count':27,'method_disagreement_count':39,
              'fixed_cost_changes_decision_count':1,'quote_effect_changes_decision_count':1}
    require(all(summary[k]==v for k,v in expected.items()),'Frozen summary counts')
    require(summary['difference_driver_counts']=={'MULTIPLE':26,'OBJECTIVE_DIFFERENCE':1},'Driver counts')
    require(summary['amount_candidate_exclusion_or_selected_binding_scenario_counts']==
            {'lp_absolute_stress':34,'concentration':31,'staking_stress':13,'cash_deadline':4},'Diagnostic counts')
    for m,(rec,idle) in zip(METHODS,((45,4),(45,4),(35,14),(36,13))):
        subset=[r for r in rows if r['method_id']==m]
        require(summary['method_counts'][m]=={'rows':49,'recommendation_rows':rec,'idle_rows':idle},'Method summary counts')
        require(len(subset)==49 and sum(r['idle_weight']=='1' for r in subset)==idle,'Method raw counts')
    for row in rows:
        require(set(row['allocation_weights'])==set(STRATEGIES) and row['allocation_weights'][ASCEND]=='0','Strategy universe / Ascend gate')
        require(sum(Decimal(x) for x in row['allocation_weights'].values())+Decimal(row['idle_weight'])==1,'Sleeve weight sum')
        require(row['whole_portfolio_compliance']=='NOT_ASSESSED' and row['evidence_mode']==LABEL,'Scope/evidence boundary')
    require(all(r['idle_weight']==1 for r in raw['production_baseline']['runs']),'Production idle baseline')
    lookup={(r['scenario_id'],r['method_id']):r for r in rows}
    require(sum(lookup[(s['scenario_id'],METHODS[2])]['allocation_weights']!=lookup[(s['scenario_id'],METHODS[3])]['allocation_weights'] for s in scenarios)==27,'Raw disagreement count')


def csv_data(headers,rows):
    out=io.StringIO(newline='');writer=csv.writer(out,lineterminator='\n');writer.writerow(headers);writer.writerows(rows)
    return out.getvalue().encode()


def json_data(value):
    return (json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()


def pct(value):
    return format((Decimal(str(value))*100).quantize(Decimal('0.1'),rounding=ROUND_HALF_EVEN),'f')+'%'


def money(value):
    try:d=Decimal(str(value))
    except Exception:return str(value)
    return ('-$' if d<0 else '$')+format(abs(d).quantize(Decimal('.01'),rounding=ROUND_HALF_EVEN),',.2f')


def allocation(row):
    return ', '.join(ASSET_LABELS[s]+' '+pct(row['allocation_weights'][s]) for s in STRATEGIES if Decimal(row['allocation_weights'][s])>0) or 'None (idle)'


def delta_rows(raw,config):
    lookup={(r['scenario_id'],r['method_id']):r for r in raw['rows']};rows=[]
    for scenario in config['scenarios']:
        sid=scenario['scenario_id'];a=lookup[(sid,METHODS[3])];b=lookup[(sid,METHODS[2])]
        if a['profit_comparability']==b['profit_comparability']=='DIRECT_COMMON_RESCORE':
            d=Decimal(a['expected_net_profit'])-Decimal(b['expected_net_profit'])
            rows.append([sid,fmt(d),'POSITIVE' if d>0 else 'NEGATIVE' if d<0 else 'ZERO',a['expected_net_profit'],b['expected_net_profit']])
    return rows


def table_specs(raw,summary,config):
    rows=raw['rows'];lookup={(r['scenario_id'],r['method_id']):r for r in rows};tables={}
    def add(name,title,headers,data,note):tables[name]={'title':title,'headers':headers,'rows':data,'note':note}
    add('01_capabilities','Method selection capabilities',['Feature',*METHOD_LABELS.values()],
        [[feature.replace('_',' ').capitalize(),*(config['capabilities'][m][feature] for m in METHODS)] for feature in config['capabilities'][METHODS[0]]],
        'Selection-time capabilities from the accepted contract. Common post-selection diagnostics do not add selection capabilities. APPROXIMATED/LEGACY_ONLY semantics remain in data/final_evaluation_contract.md.')
    add('02_matrix','Deterministic synthetic evaluation matrix',['Measure','Count'],
        [[name,summary[key]] for name,key in [('Total scenarios','total_scenarios'),('Core scenarios','core_scenarios'),('Core rows','core_rows'),('Targeted scenarios','targeted_scenarios'),('Normalized rows','normalized_rows')]]+
        [[METHOD_LABELS[m]+' rows',summary['method_counts'][m]['rows']] for m in METHODS],LABEL)
    add('03_outcomes','Method outcomes in the defined synthetic matrix',['Method','Recommendation rows','Idle rows','Recommendation rate'],
        [[METHOD_LABELS[m],summary['method_counts'][m]['recommendation_rows'],summary['method_counts'][m]['idle_rows'],
          pct(Decimal(summary['method_counts'][m]['recommendation_rows'])/summary['method_counts'][m]['rows'])] for m in METHODS],MATRIX_NOTE)
    representatives=[]
    for sid in REPRESENTATIVES:
        for m in METHODS:
            row=lookup[(sid,m)]
            reasons=list(row['binding_constraints']) if m==METHODS[3] else ['Final policy not enforced']
            if row['idle_weight']=='1':
                reasons.insert(0,'Idle selected; exclusions below are diagnostics, not isolated causes')
                reasons += [sid+':'+reason for sid,rs in row['rejection_reasons'].items() for reason in rs if sid!=ASCEND][:2]
            if sid=='ASCEND_ATTRACTIVE':reasons.insert(0,'Ascend gate CLOSED')
            if row['diagnostics'].get('candidate_policy_exclusions'):
                reasons += ['Candidate exclusion: '+k for k,v in row['diagnostics']['candidate_policy_exclusions'].items() if v]
            representatives.append([sid,METHOD_LABELS[m],allocation(row),pct(row['idle_weight']),
                row['expected_net_profit'] if row['profit_comparability']=='DIRECT_COMMON_RESCORE' else 'NOT_ASSESSED (LIMITED)',
                row['lp_absolute_stress'],row['deadline_compatibility'],'; '.join(dict.fromkeys(reasons)) or 'No selected boundary'])
    add('04_representative_scenarios','Representative frozen scenario results',
        ['Scenario ID','Method','Selected allocation','Idle','Common net profit USD','LP absolute stress','Deadline state','Constraint / rejection diagnostic'],representatives,
        'Common profit is an exact-allocation post-selection rescore. LP stress for baselines/legacy is posthoc, not enforced final risk. Unsupported deadline checks are not passes. Raw row identity: (scenario ID, method ID).')
    deltas=delta_rows(raw,config);signs=Counter(r[2] for r in deltas)
    add('05_disagreements','Legacy vs amount-aware comparison',['Measure','Value'],
        [['Comparable scenarios',len(deltas)],['Allocation disagreements',summary['amount_vs_legacy_allocation_difference_count']],
         ['Same allocation',summary['total_scenarios']-summary['amount_vs_legacy_allocation_difference_count']],
         ['Mean common-rescore delta USD',summary['mean_comparable_profit_delta']],['Median common-rescore delta USD',summary['median_comparable_profit_delta']]]+
        [[s+' profit deltas',signs[s]] for s in ('POSITIVE','NEGATIVE','ZERO')]+
        [[driver,count] for driver,count in summary['difference_driver_counts'].items()],
        'Allocation disagreement is distinct from profit improvement. Common post-selection rescore is not the legacy internal objective; selection-objective comparability remains LIMITED. No percentage-performance claim.')
    add('06_constraint_diagnostics','Scenario-level candidate exclusion / selected-binding diagnostics',['Constraint','Scenario count'],
        [[label,summary['amount_candidate_exclusion_or_selected_binding_scenario_counts'][key]] for key,label in DIAGNOSTIC_NAMES.items()],DIAGNOSTIC_NOTE)
    add('07_causality','Paired sensitivity versus diagnostic association',['Feature','Evidence kind','Source cases / diagnostic','Interpretation'],
        [['Fixed cost','CONTROLLED_PAIRED_SENSITIVITY','FIXED_100 vs FIXED_ZERO_CONTROL','Within-model cost ablation changes the selected decision'],
         ['Quote curve','CONTROLLED_PAIRED_SENSITIVITY','QUOTE_CURVE vs QUOTE_CONSTANT_CONTROL','Within-model curve ablation changes the selected LP amount']]+
        [[feature,'DIAGNOSTIC_ASSOCIATION_ONLY','Ordinary disagreement / candidate diagnostics','Not an isolated causal effect'] for feature in
         ('LP absolute stress','Concentration','Staking stress','Cash deadline','Grid discretization','Multi-factor disagreements','Fixed cost outside the paired ablation','Quote effects outside the paired ablation')],
        'Only controlled paired ablations support isolated causal sensitivity within this synthetic model. Ordinary contributor annotations are associated diagnostics.')
    return tables


def table_markdown(spec):
    def cell(v):return str(v).replace('|','/').replace('\n',' ')
    rows=[]
    for row in spec['rows']:
        display=list(row)
        if spec['title']=='Representative frozen scenario results':
            display[4]=money(display[4]);display[5]=pct(display[5]) if display[5] is not None else 'NOT_ASSESSED'
        if spec['title']=='Legacy vs amount-aware comparison' and 'USD' in str(display[0]):display[1]=money(display[1])
        rows.append('| '+' | '.join(cell(v) for v in display)+' |')
    return ('# '+spec['title']+'\n\n'+LABEL+'\n\n| '+' | '.join(spec['headers'])+' |\n| '+' | '.join('---' for _ in spec['headers'])+' |\n'+'\n'.join(rows)+'\n\n'+spec['note']+'\n').encode()


def figure_specs(raw,summary,config):
    lookup={(r['scenario_id'],r['method_id']):r for r in raw['rows']};specs={}
    def add(id,title,kind,headers,data,caption):specs[id]={'title':title,'kind':kind,'headers':headers,'rows':data,'caption':caption}
    add('01_outcomes','Deterministic synthetic scenario outcomes','outcomes',['method','recommendation','idle'],
        [[METHOD_LABELS[m],summary['method_counts'][m]['recommendation_rows'],summary['method_counts'][m]['idle_rows']] for m in METHODS],MATRIX_NOTE)
    def allocations(ids,methods=METHODS):
        return [[sid,METHOD_LABELS[m],*(lookup[(sid,m)]['allocation_weights'][s] for s in STRATEGIES),lookup[(sid,m)]['idle_weight']] for sid in ids for m in methods]
    # Mid-profile / mid-notional / mid-horizon; selected by design coordinates,
    # not by maximizing a common profit advantage.
    sid='CORE_BALANCED_1000_90'
    add('02_allocations','Representative core allocation: Balanced / 1000 0G / 90 days','allocation',
        ['scenario_id','method',*STRATEGIES,'idle'],allocations([sid]),
        'Middle profile, notional and horizon of the core design, selected without ranking profit advantage. All six sleeve components shown; Ascend is CLOSED. Different capability sets remain explicit.')
    for id,title,ids,caption in [
        ('03_fixed_cost','Controlled synthetic fixed-cost sensitivity',('FIXED_100','FIXED_ZERO_CONTROL','FIXED_1000','FIXED_10000'),
         'FIXED_100 vs FIXED_ZERO_CONTROL is a controlled fixed-cost paired ablation at the same notional. Larger-notional cases are contextual sensitivities, not the paired ablation.'),
        ('04_quote_curve','Controlled synthetic LP quote-curve sensitivity',('QUOTE_CURVE','QUOTE_CONSTANT_CONTROL'),
         'Controlled curve ablation with identical return, notional and policy. Exact candidate quote economics change Jaine exposure within the synthetic model.'),
        ('05_profiles','Synthetic LP profile progression',('LP_PROGRESSION_CONSERVATIVE','LP_PROGRESSION_BALANCED','LP_PROGRESSION_AGGRESSIVE'),
         'Profile-specific concentration, LP absolute-stress policy and discrete grid jointly constrain the selected Jaine exposure. This is not an isolated LP-risk causal estimate.'),
        ('06_deadlines','Cash-deadline effect under modelled exit timing',('DEADLINE_STAKING_1','DEADLINE_STAKING_8','DEADLINE_STAKING_15'),
         'MODELLED / SYNTHETIC_EVALUATION_ONLY timing: one day excludes asynchronous staking; eight days permits Native; fifteen permits both. No live withdrawal guarantee.')]:
        data=allocations(ids,(METHODS[3],));headers=['scenario_id','method',*STRATEGIES,'idle']
        if id=='04_quote_curve':
            headers += ['common_profit_usd','quote_loss_usd']
            for row in data:
                source=lookup[(row[0],METHODS[3])];row += [source['expected_net_profit'],source['lp_quote_execution_loss']]
        add(id,title,'allocation',headers,data,caption)
    add('07_profit_deltas','Common post-selection rescore delta: amount-aware minus legacy','delta',
        ['scenario_id','delta_usd','sign','amount_common_profit_usd','legacy_common_profit_usd'],delta_rows(raw,config),
        'All comparable scenarios in frozen scenario order. Positive, zero and negative deltas are distinct. Common exact-allocation rescore differs from the legacy selection objective, whose comparability is LIMITED. No percentage-performance claim.')
    add('08_constraints','Scenario-level candidate exclusion / selected-binding diagnostics','diagnostics',['constraint','scenario_count'],
        [[label,summary['amount_candidate_exclusion_or_selected_binding_scenario_counts'][key]] for key,label in DIAGNOSTIC_NAMES.items()],DIAGNOSTIC_NOTE)
    return specs


def render_figure(spec):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    colors=['#4477AA','#66AA55','#DD9944','#AA5599','#CC6677','#B8BDC6']
    with plt.rc_context({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold'}):
        fig,ax=plt.subplots(figsize=(10,5.5));kind=spec['kind'];rows=spec['rows']
        if kind=='outcomes':
            x=np.arange(len(rows));ax.bar(x,[r[1] for r in rows],color=colors[0],label='Recommendation')
            ax.bar(x,[r[2] for r in rows],bottom=[r[1] for r in rows],color=colors[-1],label='Idle')
            for i,r in enumerate(rows):
                ax.text(i,r[1]/2,str(r[1]),ha='center',va='center',color='white',weight='bold')
                ax.text(i,r[1]+r[2]/2,str(r[2]),ha='center',va='center',fontsize=9)
            ax.set_xticks(x,[r[0].replace('Policy-Aware ','Policy-Aware\n') for r in rows]);ax.set_ylabel('Defined scenario count');ax.legend(loc='upper left',bbox_to_anchor=(1,1))
        elif kind=='allocation':
            x=np.arange(len(rows));bottom=np.zeros(len(rows))
            for i,s in enumerate((*STRATEGIES,'idle')):
                vals=[float(Decimal(r[i+2])*100) for r in rows]
                ax.bar(x,vals,bottom=bottom,color=colors[i],label=ASSET_LABELS.get(s,'Idle'))
                for j,v in enumerate(vals):
                    if v>=8:ax.text(j,bottom[j]+v/2,f'{v:.1f}%',ha='center',va='center',color='white' if i<5 else '#222222',fontsize=9)
                bottom+=vals
            names=[r[1] if spec is not None and len({r[0] for r in rows})==1 else r[0].replace('LP_PROGRESSION_','').replace('DEADLINE_STAKING_','Deadline ').replace('QUOTE_CONSTANT_CONTROL','Constant control').replace('QUOTE_CURVE','Quote curve').replace('FIXED_ZERO_CONTROL','100, zero-cost\ncontrol').replace('FIXED_','Fixed cost, ') for r in rows]
            ax.set_xticks(x,names);ax.set_ylabel('Decision-sleeve allocation (%)');ax.set_ylim(0,100);ax.legend(loc='upper left',bbox_to_anchor=(1,1))
            if 'common_profit_usd' in spec['headers']:
                for i,row in enumerate(rows):
                    ax.text(i,78,'Common profit '+money(row[-2])+'\nQuote loss '+money(row[-1]),ha='center',va='center',fontsize=10,
                        bbox={'boxstyle':'round,pad=.4','facecolor':'white','edgecolor':'#AAAAAA'})
        elif kind=='delta':
            y=np.arange(len(rows));values=[float(r[1]) for r in rows]
            # Full scenario identities remain readable in the exported figure.
            fig.set_size_inches(12,12)
            ax.barh(y,values,color=[colors[1] if v>0 else colors[4] if v<0 else colors[-1] for v in values])
            ax.scatter([0 for v in values if v==0],[i for i,v in enumerate(values) if v==0],color='#777777',s=10,label='Zero')
            ax.set_yticks(y,[r[0] for r in rows],fontsize=7);ax.invert_yaxis();ax.axvline(0,color='#333333',linewidth=.7)
            ax.set_xlabel('Common exact-allocation rescore delta (USD)');ax.grid(axis='x',alpha=.15)
            from matplotlib.patches import Patch
            ax.legend(handles=[Patch(color=colors[1],label='Positive'),Patch(color=colors[4],label='Negative'),Patch(color=colors[-1],label='Zero')],loc='lower right')
        else:
            x=np.arange(len(rows));ax.bar(x,[r[1] for r in rows],color=colors[0])
            ax.set_xticks(x,[r[0] for r in rows]);ax.set_ylabel('Scenario count (nonexclusive diagnostics)')
            for i,r in enumerate(rows):ax.text(i,r[1]+.4,str(r[1]),ha='center')
            ax.set_ylim(0,max(r[1] for r in rows)*1.2)
        ax.set_title(spec['title'],fontsize=12,pad=16,wrap=True)
        fig.text(.5,.015,LABEL+' — defined deterministic matrix',ha='center',fontsize=9,color='#555555')
        fig.tight_layout(rect=(0,.05,1,1))
        out=io.BytesIO();fig.savefig(out,format='png',dpi=180,metadata={'Software':VERSION});plt.close(fig)
        return out.getvalue()


def findings(raw,summary,config):
    deltas=delta_rows(raw,config);signs=Counter(r[2] for r in deltas)
    machine={'version':FINDINGS_VERSION,'label':LABEL,'scope':'DECISION_SLEEVE','whole_portfolio_compliance':'NOT_ASSESSED',
        'allocation_disagreements':summary['amount_vs_legacy_allocation_difference_count'],'scenario_count':summary['total_scenarios'],
        'profit_delta_sign_counts':dict(signs),'profit_basis':'COMMON_POST_SELECTION_EXACT_ALLOCATION_RESCORE',
        'mean_profit_delta_usd':summary['mean_comparable_profit_delta'],'median_profit_delta_usd':summary['median_comparable_profit_delta'],
        'controlled_pairs':[['FIXED_100','FIXED_ZERO_CONTROL'],['QUOTE_CURVE','QUOTE_CONSTANT_CONTROL']],
        'ordinary_contributors':'DIAGNOSTIC_ASSOCIATION_NOT_ISOLATED_CAUSAL_EFFECT','deployment':'NOT_REQUIRED_NOT_PLANNED_NOT_PERFORMED'}
    q=summary
    document=f'''# Capstone findings — {FINDINGS_VERSION}

{LABEL}. Derived exclusively from accepted {config['version']} artifacts at `{SOURCE_HEAD}`. This document freezes interpretation for later proposal work; the proposal itself is unchanged.

## 1. Evaluation scope

The evaluation is deterministic, synthetic and DECISION_SLEEVE only. It compares exactly four methods over {q['total_scenarios']} scenarios / {q['normalized_rows']} rows, covering exactly five independent MVP strategies. Existing holdings/LP NFTs/pending exits remain exogenous and whole-portfolio compliance is NOT_ASSESSED. Ascend is canonically CLOSED and has zero recommendation weight in every row. No public deployment is required or planned; these results make no execution-readiness or public deployment claim.

## 2. Different allocation behavior

The policy-aware amount-aware optimizer produced a different allocation from the legacy linear optimizer in {q['amount_vs_legacy_allocation_difference_count']} of the {q['total_scenarios']} defined deterministic synthetic scenarios. This is a result over the defined experiment matrix, not an estimate of real-world disagreement probability. Any-method allocation disagreement appears in {q['method_disagreement_count']} scenarios. An allocation disagreement does not itself establish profit improvement.

## 3. Economics nonlinearity

**Fixed-cost controlled paired ablation:** FIXED_100 versus FIXED_ZERO_CONTROL holds notional, return, horizon and policy constant while removing the fixed lifecycle charge. The frozen final-method allocation changes from idle to positive Native exposure. Charging fixed costs once at the actual candidate amount can make small allocations uneconomic. FIXED_1000 and FIXED_10000 provide additional notional sensitivity context. This is causal sensitivity within the synthetic model only.

**Quote-curve controlled paired ablation:** QUOTE_CURVE versus QUOTE_CONSTANT_CONTROL holds return, notional and policy constant while removing the amount slope of the synthetic LP quote curve. The chosen Jaine amount changes. Exact candidate quote assumptions can change selected LP allocation within this model. This is the second supported paired causal sensitivity; neither pair establishes an observed market effect.

## 4. Profile and risk feasibility

LP_PROGRESSION_CONSERVATIVE, LP_PROGRESSION_BALANCED and LP_PROGRESSION_AGGRESSIVE select Jaine {pct(next(r for r in raw['rows'] if r['scenario_id']=='LP_PROGRESSION_CONSERVATIVE' and r['method_id']==METHODS[3])['allocation_weights'][JAINE])}, {pct(next(r for r in raw['rows'] if r['scenario_id']=='LP_PROGRESSION_BALANCED' and r['method_id']==METHODS[3])['allocation_weights'][JAINE])} and {pct(next(r for r in raw['rows'] if r['scenario_id']=='LP_PROGRESSION_AGGRESSIVE' and r['method_id']==METHODS[3])['allocation_weights'][JAINE])}, respectively, under the same LP economics. Profile-dependent feasibility changes exposure through the combination of concentration limits, LP absolute-stress policy and the discrete grid. The entire progression cannot be attributed to LP stress alone. Absolute LP loss is the total position-loss measure; IL and HODL market loss remain diagnostics and are not added again.

## 5. Liquidity and cash deadlines

An explicit cash deadline can make an otherwise economically attractive asynchronous strategy infeasible. DEADLINE_STAKING_1 excludes Native/Gimo from the final allocation; DEADLINE_STAKING_8 permits Native but not Gimo; DEADLINE_STAKING_15 permits both. The underlying durations are MODELLED / SYNTHETIC_EVALUATION_ONLY. They are not guaranteed withdrawal times or observations of live liquidity. Holding horizon, time-to-cash after an exit decision and cash deadline are distinct.

## 6. Abstention is a valid decision

Keeping capital idle is a first-class optimizer outcome rather than a failure state. NEGATIVE, MISSING_RETURN, MISSING_COST, QUOTE_MISMATCH, ADMISSION_FAILURE and DEADLINE_STAKING_1 show different reasons for abstention. Risk feasibility can also exclude positive candidate allocations without forcing all scenarios idle. Missing required return/cost/quotes never become zero evidence. Canonical production runs remain 100% idle for all three profiles because runtime binding/admission/economics are unresolved, separately from synthetic evaluation outcomes. Idle causes must remain distinguishable.

## 7. Legacy comparison

The unchanged legacy optimizer is a simpler/reference approximation, not characterized as wrong. It uses reference-notional linearization, fractionally scales reference effects that are actually fixed/amount-dependent, uses the legacy LP stress proxy and legacy exit limits, and lacks final cash-deadline/range-risk semantics. The final method uses exact candidate economics, fixed cost once, exact-amount LP quotes, range-aware LP absolute stress, cash-deadline feasibility and selected-point economics/policy revalidation. These capability differences are explicit in Table 1; common rescoring does not retrofit capabilities into a baseline.

## 8. Profit comparison

Under the common exact-allocation rescore used solely for comparison, the defined matrix has a positive mean amount-aware-minus-legacy profit delta ({money(q['mean_comparable_profit_delta'])}), while the median is zero ({money(q['median_comparable_profit_delta'])}). Across {len(deltas)} comparable cases, {signs['POSITIVE']} deltas are positive, {signs['NEGATIVE']} negative and {signs['ZERO']} zero. Not all disagreements improve profit. Common post-selection rescore is not the legacy optimizer's own objective; selection-objective comparability is LIMITED. {q['limited_profit_rows']} simple-baseline rows lack qualified common economics and are separately LIMITED. No percentage-return superiority, forecast accuracy or production-performance claim follows. TIE has equal common profit and different secondary selection behavior.

## 9. Causal sensitivity versus diagnostic association

Only the controlled fixed-cost and quote-curve paired ablations support isolated causal sensitivity within this synthetic model. Ordinary contributor annotations for LP stress, staking stress, concentration, deadline, grid, fixed cost and quote effects are diagnostic association, not isolated causal effects. MULTIPLE classifications retain more than one contributor. Table 7 and figure captions preserve this distinction. The constraint counts concern candidate exclusion or selected binding and are nonexclusive deterministic scenario counts, not probabilities or real-world frequencies.

## 10. Limitations

- Synthetic economic inputs and modelled 0G valuation.
- Synthetic analytical quote curve, not captured executable market quotes.
- Modelled deterministic stress assumptions and modelled exit durations.
- Ascend gate CLOSED; hypothetical economic analysis does not make it allocatable.
- No public deployment, no live admission and no execution-ready proof.
- No observational freshness policy is established by this evaluation; canonical evidence remains empty.
- No whole-portfolio optimization or compliance assessment.
- Discrete 0.1 amount grid limits attainable weights.
- Legacy selection objective is only partially comparable to final exact economics.
- The deterministic matrix is not statistically representative; it provides no probabilities, confidence intervals or forecasts.
- Independent stress budgets do not imply correlated joint events.
- Findings cover the chosen synthetic ranges and assumptions, not optimal or deployed LP positions.

## 11. Contribution

The capstone contributes an evidence-qualified, amount-aware decision-sleeve optimizer that separates expected economics, technical admission, deterministic risk, liquidity timing and execution proof, and demonstrates through controlled synthetic evaluation where exact candidate economics and explicit feasibility constraints alter recommendations relative to simpler allocation approaches.

## Reproduction and source integrity

Run `python tools/generate_final_results.py` and `python tools/generate_final_results.py --check`. The generator verifies pinned source SHA-256 hashes and counts without invoking an optimizer. The manifest lists sources, outputs, figure data, captions and this document's hash. CSVs retain accepted numerical precision; Markdown/figure labels round percentages to one decimal and currency to cents. Matplotlib Agg / DejaVu Sans PNGs have fixed metadata and no timestamp. Exact figure bytes require the renderer/font versions fingerprinted in the manifest; check mode fails on drift. Install the optional pinned renderer with `python -m pip install -r requirements-results.txt` when needed.

Iteration 24 presents and interprets the frozen Iteration 23 deterministic synthetic evaluation. Its figures and findings describe behavior within the defined experiment matrix and do not constitute empirical market probabilities, forecasts, live execution results or proof of production performance.
'''
    return machine,document.encode()


def generate(root=ROOT):
    raw,summary,config=read_sources(root);outputs={};tables=table_specs(raw,summary,config);figures=figure_specs(raw,summary,config)
    for name,spec in tables.items():
        base='results/final_tables/'+name
        outputs[base+'.csv']=csv_data(spec['headers'],spec['rows']);outputs[base+'.md']=table_markdown(spec)
    captions=['# Final figure captions\n\n'+LABEL+'\n']
    for name,spec in figures.items():
        base='results/final_figures/'+name
        outputs[base+'.png']=render_figure(spec)
        outputs[base+'_data.csv']=csv_data(spec['headers'],spec['rows'])
        captions.append('## '+name+' — '+spec['title']+'\n\n'+spec['caption']+'\n')
    outputs['results/final_figures/captions.md']=('\n'.join(captions).rstrip()+'\n').encode()
    machine,document=findings(raw,summary,config)
    outputs['results/final_evaluation_findings.json']=json_data(machine)
    outputs['docs/final_evaluation_findings_iteration24.md']=document
    import matplotlib
    from matplotlib import font_manager,ft2font
    font=Path(font_manager.findfont('DejaVu Sans'))
    manifest={'generator_version':VERSION,'findings_version':FINDINGS_VERSION,'label':LABEL,'source_head':SOURCE_HEAD,
        'source_sha256':SOURCE_HASHES,'table_files':[p for p in outputs if p.startswith('results/final_tables/')],
        'figure_files':[p for p in outputs if p.endswith('.png')],'figure_data_files':[p for p in outputs if p.endswith('_data.csv')],
        'findings_document':'docs/final_evaluation_findings_iteration24.md',
        'findings_document_sha256':sha256(document).hexdigest(),
        'generator_source_sha256':{p:sha256((ROOT/p).read_bytes()).hexdigest() for p in
            ('src/ascend_optimizer/final_results.py','tools/generate_final_results.py','requirements-results.txt')},
        'output_sha256':{p:sha256(v).hexdigest() for p,v in sorted(outputs.items())},
        'renderer':{'matplotlib':matplotlib.__version__,'backend':'Agg','freetype':ft2font.__freetype_version__,
                    'font_family':'DejaVu Sans','font_sha256':sha256(font.read_bytes()).hexdigest(),'png_software_tag':VERSION},
        'counts':{'tables':len(tables),'figures':len(figures),'source_scenarios':len(config['scenarios']),'source_rows':len(raw['rows'])},
        'reproduction_command':'python tools/generate_final_results.py', 'check_command':'python tools/generate_final_results.py --check',
        'check_semantics':'Exact bytes for all generated outputs including PNGs and manifest; renderer/font drift fails closed',
        'optimizer_invoked':False,'iteration23_sources_modified':False}
    outputs['results/final_results_iteration24_manifest.json']=json_data(manifest)
    return outputs
