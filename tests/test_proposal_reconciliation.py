"""Lightweight staging-contract checks; no application/model or proposal mutation."""
from pathlib import Path
import re
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
DRAFT = ROOT/'docs/proposal_reconciliation_iteration27.md'
BASE = '4bbe78dc621036e9f6b692af386f458c7b9311f3'
TEXT = DRAFT.read_text()
MATRIX = TEXT.split('## Reconciliation matrix')[1].split('## Proposal source and audit boundaries')[0]
ROWS = [line.split('|')[1:-1] for line in MATRIX.splitlines()
        if line.startswith('| ') and not line.startswith('| Proposal section')]
ROWS = [[cell.strip() for cell in row] for row in ROWS]
BLOCKS = re.findall(r'### P\d+ — Proposal Section (.*?)\n(.*?)(?=\n### P|\n## Recommended Table|\Z)',TEXT,re.S)


def test_staging_labels_and_source_grounding():
    assert 'PROPOSAL_RECONCILIATION_DRAFT' in TEXT
    assert 'NOT_YET_APPLIED_TO_FINAL_PROPOSAL' in TEXT
    assert '1KTTxjkWtZv773_iQ-XisBlF-zA7PjeJZGDfAXy-w1d4' in TEXT
    assert 'normalized readable-text snapshot' in TEXT and BASE in TEXT
    assert 'not a rendered-page/layout assessment' in TEXT


@pytest.mark.parametrize('row',ROWS,ids=[row[0] for row in ROWS])
def test_one_action_and_amendment_coverage(row):
    section,state,action,reason,basis = row
    assert action in {'KEEP','AMEND','REPLACE','ADD','REMOVE'}
    assert len(reason)>45 and state
    source=basis.strip('`')
    assert (ROOT/source).is_file()
    matches=[body for name,body in BLOCKS if name==section]
    if action=='KEEP':
        assert not matches
    else:
        assert len(matches)==1
        assert f'**Action:** {action}' in matches[0]
        assert '**Frozen basis:**' in matches[0] and source in matches[0]
        if action=='REMOVE': assert '**Removal recommendation:**' in matches[0]
        else: assert '**Proposed proposal text:**' in matches[0] and '\n> ' in matches[0]


def test_action_totals_and_uniqueness():
    from collections import Counter
    assert len(ROWS)==63
    assert len({r[0] for r in ROWS})==63
    assert Counter(r[2] for r in ROWS)==dict(KEEP=7,AMEND=29,REPLACE=19,ADD=6,REMOVE=2)
    assert sum('**Proposed proposal text:**' in body for _,body in BLOCKS)==54


@pytest.mark.parametrize('term',[
    '1.0 Objectives','3.1 Overview','4.0.1 Asset','4.1 MVP Strategy','4.2 Net Return',
    '4.3 Risk','4.3.1 Exit','4.4 Risk Profiles','4.5 Recommendation',
    '5.1 Core','6.2 Strategy Snapshot','6.2.1 Freshness','6.3 Data Sources',
    '6.4 Evaluation Plan','6.5 Deterministic','6.6 Limitations','8.6 Conclusion',
    'Figure 5.3','Table 6.1','NOT_ESTABLISHED','NOT_ASSESSED','EXOGENOUS_NOT_OPTIMIZED',
    'SYNTHETIC_EVALUATION_ONLY','27 of the 49','19 cases, negative in 7 and zero in 23',
    '+$43.40 and median $0','fixed-cost and quote-curve','not statistically representative'])
def test_required_areas_and_claim_boundaries(term):
    assert term in TEXT


def test_frozen_artifact_map_paths_and_selection():
    mapping=TEXT.split('## Recommended Table and Figure Integration')[1].split('## Proposal consistency checklist')[0]
    paths=re.findall(r'`(results/final_(?:tables|figures)/[^`]+)`',mapping)
    assert len(paths)==15 and len(set(paths))==15
    for path in paths: assert (ROOT/path).is_file()
    lines=[line for line in mapping.splitlines() if line.startswith('| `results/')]
    assert sum('| RECOMMENDED |' in line for line in lines)==7
    assert sum('| OPTIONAL |' in line for line in lines)==5
    assert sum('| DO_NOT_INCLUDE |' in line for line in lines)==3
    assert 'not isolated causal' in TEXT or 'not an isolated causal' in TEXT


def test_documentation_only_change_and_all_frozen_files_exact():
    allowed={'docs/proposal_reconciliation_iteration27.md','tests/test_proposal_reconciliation.py'}
    changed=subprocess.check_output(['git','diff',BASE,'--name-only'],cwd=ROOT).decode().splitlines()
    untracked=subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=ROOT).decode().splitlines()
    assert set(changed+untracked)<=allowed
    # Compare every tracked frozen file, not just result hashes or a few examples.
    paths=subprocess.check_output(['git','ls-tree','-r','--name-only',BASE],cwd=ROOT).decode().splitlines()
    for path in paths:
        if path in allowed: continue
        expected=subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT)
        assert (ROOT/path).read_bytes()==expected,path
