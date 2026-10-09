"""Deployment-free design checks. Supplied parameters are SYNTHETIC_PREFLIGHT_ONLY."""
from copy import deepcopy
import json
from pathlib import Path
import runpy

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE = runpy.run_path(str(ROOT / 'tools/deployment_preflight.py'))
DESIGN = json.loads((ROOT / 'data/intended_deployment_architecture.json').read_text())
NATIVE, GIMO, JAINE, OKU, ASCEND = MODULE['STRATEGIES']
LABEL = 'SYNTHETIC_PREFLIGHT_ONLY'


def addr(number):
    return '0x' + format(number, '040x')


def params(sid):
    """Ephemeral structural examples, not protocol/config/admission assertions."""
    if sid == NATIVE:
        return {'initial_owner': addr(1), 'vault': addr(2), 'validator': addr(3)}
    if sid == GIMO:
        return {'vault': addr(2), 'stake_pool': addr(3), 'st0g': addr(4), 'referral': ''}
    if sid in {JAINE, OKU}:
        return {'vault': addr(2), 'factory': addr(3), 'router': addr(4), 'position_manager': addr(5),
                'pool': addr(6 if sid == JAINE else 7), 'w0g': addr(8), 'usdce': addr(9),
                'token0': addr(8), 'token1': addr(9), 'fee_tier': 3000, 'tick_spacing': 60,
                'tick_lower': -600, 'tick_upper': 600, 'sqrt_lower_x96': 100, 'sqrt_upper_x96': 200,
                'target_usdc_bps': 4500 if sid == JAINE else 5500,
                'router_mode': 'V1' if sid == JAINE else 'ROUTER02'}
    return {'vault': addr(2), 'source_core': addr(3), 'a0g': addr(3), 'w0g': addr(4),
            'withdrawal_queue': addr(5), 'source_asset': addr(4), 'queue_asset': addr(4),
            'queue_source_core': addr(3)}


def validate(sid, p=None):
    return MODULE['validate_route_parameters'](sid, 16661, p or params(sid), evidence_label=LABEL)


def test_canonical_design_has_exactly_five_and_no_deployment_requirement():
    result = MODULE['validate_design'](DESIGN)
    assert result['strategy_count'] == 5 and result['execution_chain_id'] == 16661
    assert result['public_deployment'] == 'NOT_DEPLOYED'
    assert result['public_deployment_required'] is False
    assert 'W0G' not in MODULE['STRATEGIES']
    assert not DESIGN['public_deployment_planned']


@pytest.mark.parametrize('change', ['sixth', 'chain', 'claim', 'required', 'ascend_gate', 'resolved_validator', 'component_chain', 'dependency_chain'])
def test_invalid_architecture_claims_rejected(change):
    d = deepcopy(DESIGN)
    if change == 'sixth': d['strategies'].append(deepcopy(d['strategies'][0]))
    elif change == 'chain': d['execution_chain_id'] = 16602
    elif change == 'claim': d['strategies'][0]['readiness']['public_deployment'] = 'PERFORMED'
    elif change == 'required': d['public_deployment_required'] = True
    elif change == 'ascend_gate': d['strategies'][-1]['allocation_gate'] = 'CONDITIONAL'
    elif change == 'resolved_validator':
        next(c for c in d['strategies'][0]['components'] if c['component'] == 'validator')['value'] = addr(30)
    elif change == 'component_chain': d['strategies'][1]['components'][5]['chain_id'] = 8453
    else: d['dependency_domains'][0]['chain_id'] = 16661
    with pytest.raises(ValueError): MODULE['validate_design'](d)


@pytest.mark.parametrize('sid', list(MODULE['STRATEGIES']))
def test_synthetic_complete_structural_checks_never_produce_runtime_proof(sid):
    result = validate(sid)
    assert result['evidence_class'] == LABEL
    assert result['runtime_binding'] == 'UNRESOLVED_RUNTIME_BINDING'
    assert result['public_deployment'] == 'NOT_DEPLOYED'
    assert 'config_identity' not in result and 'verification_state' not in result


@pytest.mark.parametrize('chain', [16602, 1, 8453])
def test_other_network_cannot_substitute_for_intended_execution(chain):
    with pytest.raises(ValueError, match='16661'):
        MODULE['validate_route_parameters'](NATIVE, chain, params(NATIVE), evidence_label=LABEL)


@pytest.mark.parametrize('sid', [JAINE, OKU])
@pytest.mark.parametrize('field,value', [
    ('token0', addr(10)), ('token1', addr(8)), ('fee_tier', 0), ('fee_tier', 2**24),
    ('tick_spacing', 0), ('tick_lower', -599), ('tick_lower', 600),
    ('tick_lower', -887273), ('sqrt_lower_x96', 0), ('sqrt_upper_x96', 100),
    ('sqrt_upper_x96', 2**160), ('target_usdc_bps', 0), ('target_usdc_bps', 10000),
    ('target_usdc_bps', 45.5), ('pool', None),
])
def test_lp_pair_tick_range_target_structural_validation(sid, field, value):
    p = params(sid); p[field] = value
    with pytest.raises(ValueError): validate(sid, p)


@pytest.mark.parametrize('sid', [JAINE, OKU])
def test_jaine_oku_modes_are_not_interchangeable(sid):
    p = params(sid); p['router_mode'] = 'ROUTER02' if sid == JAINE else 'V1'
    with pytest.raises(ValueError, match='router ABI'): validate(sid, p)


def test_routes_independent_and_native_not_selected_from_samples():
    rows = {r['strategy_id']: {c['component']: c for c in r['components']} for r in DESIGN['strategies']}
    for key in ['factory', 'router', 'position_manager']:
        assert rows[JAINE][key]['value'] != rows[OKU][key]['value']
    for sid in [JAINE, OKU]:
        for key in ['pool', 'token0', 'token1', 'fee_tier', 'tick_spacing', 'tick_lower', 'tick_upper', 'target_usdc_bps']:
            assert rows[sid][key]['value'] is None
    assert rows[NATIVE]['validator']['value'] is None
    assert rows[GIMO]['stake_pool']['classification'] == 'EXTERNAL_PROTOCOL_REFERENCE'
    assert rows[GIMO]['referral']['value'] is None


@pytest.mark.parametrize('field', ['validator', 'vault', 'initial_owner'])
def test_native_requires_supplied_nonzero_addresses(field):
    p = params(NATIVE); p[field] = addr(0)
    with pytest.raises(ValueError, match='nonzero'): validate(NATIVE, p)


@pytest.mark.parametrize('field,value', [('referral', 1), ('st0g', addr(0)), ('stake_pool', 'not-address')])
def test_gimo_structural_fields(field, value):
    p = params(GIMO); p[field] = value
    with pytest.raises(ValueError): validate(GIMO, p)


@pytest.mark.parametrize('field', ['a0g', 'source_asset', 'queue_asset', 'queue_source_core'])
def test_ascend_share_asset_queue_relationship_checks(field):
    p = params(ASCEND); p[field] = addr(99)
    with pytest.raises(ValueError): validate(ASCEND, p)


def test_synthetic_preflight_not_accepted_as_canonical_runtime_config(tmp_path):
    from src.ascend_optimizer.runtime_config import load_runtime_configs
    from src.ascend_optimizer.data_loader import SchemaValidationError
    p = tmp_path / 'preflight.json'; p.write_text(json.dumps(validate(NATIVE)))
    with pytest.raises(SchemaValidationError): load_runtime_configs(p)
    with pytest.raises(ValueError, match=LABEL):
        MODULE['validate_route_parameters'](GIMO, 16661, params(GIMO), evidence_label='VERIFIED')


def test_frozen_runtime_configs_admission_and_gate_preserved():
    from src.ascend_optimizer.runtime_config import load_runtime_configs
    from src.ascend_optimizer.data_loader import load_strategies
    assert all(r['verification_state'] == 'UNRESOLVED' and r['config_identity'] is None for r in load_runtime_configs())
    assert len((ROOT / 'data/admission_evidence.csv').read_text().splitlines()) == 1
    rows = load_strategies()
    assert rows.loc[rows.strategy_id == ASCEND, 'allocation_gate'].item() == 'CLOSED'
