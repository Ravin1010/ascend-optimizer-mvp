"""Current-facing documentation contract, scoped separately from historical evidence."""
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
README = (ROOT/'README.md').read_text()


@pytest.mark.parametrize('text', [
    'DECISION_SLEEVE', 'EXOGENOUS_NOT_OPTIMIZED', 'NOT_ASSESSED',
    'not required and not planned', 'PRODUCTION', 'SYNTHETIC_EVALUATION_ONLY',
    'not a strategy', 'KIV_FUTURE', 'INTEGRATED_ALLOCATABLE', 'INTEGRATED_GATED',
    'EMBEDDED_NON_ALLOCATABLE', 'OBSERVED_EXCLUDED', 'AUXILIARY_NOT_STRATEGY',
    'POLICY_AWARE_AMOUNT_OPTIMIZER', 'LEGACY_COMPATIBILITY',
    'range-aware LP absolute stress loss', 'cash deadline', 'NOT_ESTABLISHED',
    'schema **1.4**', '/api/decision-sleeve', 'compatibility-only',
    'UNRESOLVED / NOT_VERIFIED', '100% idle'])
def test_current_documented_boundaries(text):
    assert text in README


def test_no_stale_primary_workflow():
    assert '## Personalized live optimizer' not in README
    assert '## Linear MVP assumption' not in README
    assert 'must be refreshed from live pool data immediately before deployment' not in README
    assert 'not an independent yield source' in README
    assert 'MODELLED_LP_STRESS_20PCT' in README and 'LEGACY_COMPATIBILITY' in README


def test_ascend_dependency_wording_is_not_lp_range():
    text = (ROOT/'docs/risk_exit_iteration21.md').read_text()
    line = next(line for line in text.splitlines() if '| ASCEND_DEPENDENCIES_UNRESOLVED |' in line)
    assert 'Direct range path' not in line
    assert 'Embedded backing/restaking dependency severity unresolved' in line
    assert 'Historical freeze-point record' in text


def test_current_state_status_and_execution_boundary():
    text = (ROOT/'docs/current_state_iteration26.md').read_text()
    assert 'ASSET_NORMALIZATION_V1' in text
    assert 'not a VERIFIED capstone record' in text
    assert 'Direct range path / unresolved' not in text
    assert 'Jaine V1 and Oku Router02 remain independent' in text
    assert 'No proposal edits, fresh evidence, public deployment or Iteration 27' in text
