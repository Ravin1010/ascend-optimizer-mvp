"""Frozen-source presentation, interpretation and exact figure replay."""
from copy import deepcopy
from decimal import Decimal
from hashlib import sha256
import csv
import io
import json
from pathlib import Path
import subprocess

from PIL import Image
import pytest
from src.ascend_optimizer import final_results as f


@pytest.fixture(scope='module')
def sources():return f.read_sources()


@pytest.fixture(scope='module')
def outputs():return f.generate()


def test_pinned_sources_version_and_matrix(sources):
    raw,s,c=sources
    assert raw['evaluation_version']=='FINAL_EVALUATION_V1'
    assert len(c['scenarios'])==49 and len(raw['rows'])==196
    assert c['methods']==list(f.METHODS)
    assert s['core_scenarios']==27 and s['core_rows']==108 and s['targeted_scenarios']==22
    assert all(r['allocation_weights'][f.ASCEND]=='0' for r in raw['rows'])


@pytest.mark.parametrize('key,value',[('evaluation_version','V2'),('total_scenarios',48),('normalized_rows',195),
    ('core_scenarios',26),('core_rows',104),('targeted_scenarios',21),('amount_vs_legacy_allocation_difference_count',26),
    ('method_disagreement_count',38),('fixed_cost_changes_decision_count',0),('quote_effect_changes_decision_count',0),
    ('difference_driver_counts',{'MULTIPLE':27}),('amount_candidate_exclusion_or_selected_binding_scenario_counts',{})])
def test_invalid_frozen_summary_fails_closed(sources,key,value):
    raw,s,c=deepcopy(sources);s[key]=value
    with pytest.raises(f.SourceIntegrityError):f.validate(raw,s,c)


@pytest.mark.parametrize('change',['ascend','methods','row_count','method_count'])
def test_raw_or_method_invariants_fail(sources,change):
    raw,s,c=deepcopy(sources)
    if change=='ascend':raw['rows'][0]['allocation_weights'][f.ASCEND]='.1'
    elif change=='methods':c['methods'].append('FIFTH')
    elif change=='row_count':raw['rows'].pop()
    else:s['method_counts'][f.METHODS[0]]['idle_rows']=3
    with pytest.raises(f.SourceIntegrityError):f.validate(raw,s,c)


def test_source_hash_tamper_fails_before_render(tmp_path):
    path=next(iter(f.SOURCE_HASHES));dest=tmp_path/path;dest.parent.mkdir(parents=True)
    dest.write_bytes((f.ROOT/path).read_bytes()+b'\n')
    with pytest.raises(f.SourceIntegrityError,match='hash mismatch'):f.read_sources(tmp_path)


def test_no_optimizer_execution(monkeypatch,outputs):
    from src.ascend_optimizer import final_evaluation as ev
    def forbidden(*a,**kw):raise AssertionError('Optimizer must not run')
    monkeypatch.setattr(ev,'run_amount_optimizer',forbidden);monkeypatch.setattr(ev,'optimize_portfolio',forbidden)
    assert f.generate()==outputs


def test_capability_table_exact(sources):
    raw,s,c=sources;table=f.table_specs(raw,s,c)['01_capabilities']
    for row,(feature,_) in zip(table['rows'],c['capabilities'][f.METHODS[0]].items(),strict=True):
        assert row[1:]==[c['capabilities'][m][feature] for m in f.METHODS]
    assert 'APPROXIMATED' in str(table) and 'LEGACY_ONLY' in str(table)


def test_table_summary_outcomes_and_diagnostics(sources):
    raw,s,c=sources;t=f.table_specs(raw,s,c)
    assert len(t)==7
    assert [r[1:3] for r in t['03_outcomes']['rows']]==[[45,4],[45,4],[35,14],[36,13]]
    assert [r[1] for r in t['06_constraint_diagnostics']['rows']]==[34,31,13,4]
    assert 'not empirical' in t['03_outcomes']['note']
    assert 'not empirical frequencies' in t['06_constraint_diagnostics']['note']


def test_representative_table_traceability_and_unsupported(sources):
    raw,s,c=sources;t=f.table_specs(raw,s,c)['04_representative_scenarios']
    lookup={(r['scenario_id'],f.METHOD_LABELS[r['method_id']]):r for r in raw['rows']}
    assert len(t['rows'])==len(f.REPRESENTATIVES)*4
    for row in t['rows']:
        source=lookup[(row[0],row[1])]
        assert row[2]==f.allocation(source) and row[3]==f.pct(source['idle_weight'])
        assert row[5]==source['lp_absolute_stress'] and row[6]==source['deadline_compatibility']
        if source['profit_comparability']=='LIMITED':assert row[4]=='NOT_ASSESSED (LIMITED)'
    assert any(row[6]=='NOT_SUPPORTED' for row in t['rows'])


def test_disagreement_profit_counts_distinct(sources):
    raw,s,c=sources;delta=f.delta_rows(raw,c)
    assert len(delta)==49
    assert {sign:sum(r[2]==sign for r in delta) for sign in ('POSITIVE','NEGATIVE','ZERO')}=={'POSITIVE':19,'NEGATIVE':7,'ZERO':23}
    table=f.table_specs(raw,s,c)['05_disagreements']
    assert ['Allocation disagreements',27] in table['rows'] and ['Same allocation',22] in table['rows']
    assert 'not the legacy internal objective' in table['note']


def test_paired_vs_association_table(sources):
    t=f.table_specs(*sources)['07_causality']
    assert [r[1] for r in t['rows'][:2]]==['CONTROLLED_PAIRED_SENSITIVITY']*2
    assert all(r[1]=='DIAGNOSTIC_ASSOCIATION_ONLY' for r in t['rows'][2:])
    assert 'FIXED_100 vs FIXED_ZERO_CONTROL' in str(t) and 'QUOTE_CURVE vs QUOTE_CONSTANT_CONTROL' in str(t)


@pytest.mark.parametrize('id',[f'{n:02d}_{name}' for n,name in enumerate(('outcomes','allocations','fixed_cost','quote_curve','profiles','deadlines','profit_deltas','constraints'),1)])
def test_all_figures_have_exact_data_and_png_metadata(outputs,id):
    base='results/final_figures/'+id
    assert base+'.png' in outputs and base+'_data.csv' in outputs
    image=Image.open(io.BytesIO(outputs[base+'.png']))
    assert image.info['Software']==f.VERSION and 'Creation Time' not in image.info
    assert image.width>=1000 and image.height>=900


def test_figure_data_traceability_and_order(sources):
    raw,s,c=sources;fig=f.figure_specs(raw,s,c);lookup={(r['scenario_id'],r['method_id']):r for r in raw['rows']}
    for spec in fig.values():
        if spec['kind']=='allocation':
            for row in spec['rows']:
                method=next(m for m,label in f.METHOD_LABELS.items() if label==row[1]);source=lookup[(row[0],method)]
                assert row[2:8]==[*(source['allocation_weights'][sid] for sid in f.STRATEGIES),source['idle_weight']]
    assert [r[1] for r in fig['02_allocations']['rows']]==list(f.METHOD_LABELS.values())
    assert 'Middle profile' in fig['02_allocations']['caption']
    assert [r[0] for r in fig['07_profit_deltas']['rows']]==[sc['scenario_id'] for sc in c['scenarios']]
    q=fig['04_quote_curve'];assert 'quote_loss_usd' in q['headers']
    for row in q['rows']:assert row[-2:]==[lookup[(row[0],f.METHODS[3])]['expected_net_profit'],lookup[(row[0],f.METHODS[3])]['lp_quote_execution_loss']]


def test_profit_figure_common_rescore_not_internal_objective(sources):
    raw,s,c=sources;spec=f.figure_specs(raw,s,c)['07_profit_deltas'];lookup={(r['scenario_id'],r['method_id']):r for r in raw['rows']}
    for row in spec['rows']:
        a=lookup[(row[0],f.METHODS[3])];b=lookup[(row[0],f.METHODS[2])]
        assert row[1]==f.fmt(Decimal(a['expected_net_profit'])-Decimal(b['expected_net_profit']))
    assert 'selection objective' in spec['caption'] and 'LIMITED' in spec['caption']


def test_figure_captions_preserve_boundaries(sources):
    specs=f.figure_specs(*sources)
    assert 'controlled' in specs['03_fixed_cost']['caption'] and 'Controlled' in specs['04_quote_curve']['caption']
    assert 'not an isolated' in specs['05_profiles']['caption']
    assert 'MODELLED / SYNTHETIC_EVALUATION_ONLY' in specs['06_deadlines']['caption']
    assert 'not empirical frequencies' in specs['08_constraints']['caption']
    for spec in specs.values():
        assert not any(phrase in spec['title'].lower() for phrase in ('success rate','real-world risks','performance improvement','market probability'))


def test_findings_required_qualifications(sources):
    machine,document=f.findings(*sources);text=document.decode()
    assert '27 of the 49 defined deterministic synthetic scenarios' in text
    assert 'not an estimate of real-world disagreement probability' in text
    assert 'FIXED_100 versus FIXED_ZERO_CONTROL' in text and 'QUOTE_CURVE versus QUOTE_CONSTANT_CONTROL' in text
    assert 'diagnostic association, not isolated causal effects' in text
    assert 'median is zero' in text and '7 negative' in text
    assert 'first-class optimizer outcome' in text and 'Not all disagreements improve profit' in text
    assert machine['profit_delta_sign_counts']=={'POSITIVE':19,'NEGATIVE':7,'ZERO':23}
    assert 'always better' not in text and 'guaranteed withdrawal times' in text and 'not guaranteed' in text


@pytest.mark.parametrize('limitation',['Synthetic economic inputs','modelled 0G valuation','quote curve','modelled exit durations',
    'Ascend gate CLOSED','No public deployment','no live admission','no execution-ready proof','No observational freshness policy',
    'No whole-portfolio optimization','Discrete 0.1','partially comparable','not statistically representative','correlated joint events'])
def test_findings_limitations(sources,limitation):
    assert limitation in f.findings(*sources)[1].decode()


def test_manifest_and_exact_committed_outputs(outputs):
    manifest=json.loads(outputs['results/final_results_iteration24_manifest.json'])
    assert manifest['source_sha256']==f.SOURCE_HASHES and manifest['counts']=={'tables':7,'figures':8,'source_scenarios':49,'source_rows':196}
    assert len(manifest['figure_data_files'])==8 and not manifest['optimizer_invoked']
    assert manifest['findings_document_sha256']==sha256(outputs[manifest['findings_document']]).hexdigest()
    for path,content in outputs.items():
        assert (f.ROOT/path).read_bytes()==content
        if path in manifest['output_sha256']:assert sha256(content).hexdigest()==manifest['output_sha256'][path]


def test_frozen_source_and_canonical_evidence_unchanged(sources):
    paths=list(f.SOURCE_HASHES)+['data/'+name for name in ('runtime_strategy_config.json','admission_evidence.csv',
        'strategy_return_evidence.json','lp_quote_evidence.json','lifecycle_cost_evidence.json','lp_evaluation_config.json',
        'evaluation_policy.json','risk_scenarios.json','exit_evaluation_config.json','strategies.csv')]
    for path in paths:
        assert (f.ROOT/path).read_bytes()==subprocess.check_output(['git','show',f.SOURCE_HEAD+':'+path],cwd=f.ROOT)
    runtime=json.loads((f.ROOT/'data/runtime_strategy_config.json').read_text());assert all(r['verification_state']=='UNRESOLVED' for r in runtime['records'])
    assert len((f.ROOT/'data/admission_evidence.csv').read_text().splitlines())==1
    for name in ('strategy_return_evidence','lp_quote_evidence','lifecycle_cost_evidence'):
        assert not json.loads((f.ROOT/f'data/{name}.json').read_text())['records']
    assert all(r['idle_weight']==1 for r in sources[0]['production_baseline']['runs'])
