"""Read-only Iteration 18 design preflight; no RPC, signing or deployment path.

python tools/deployment_preflight.py
Parameter checks assert structure only, never runtime identity/admission/code.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DESIGN_PATH = ROOT / 'data/intended_deployment_architecture.json'
STRATEGIES = {
    'NATIVE_STAKE_0G': 'Native0GStakingAdapter',
    'GIMO_STAKE_0G': 'GimoAdapter',
    'JAINE_LP_0G_USDC': 'JaineLPAdapter',
    'OKU_LP_0G_USDC': 'OkuV3Adapter',
    'ASCEND_STAKE_A0G': 'AscendProtocolAdapter',
}
CLASSES = {'SOURCE_FIXED', 'EXTERNAL_PROTOCOL_REFERENCE', 'DEPLOYMENT_TIME_INPUT',
           'UNRESOLVED_DEPLOYMENT_INPUT', 'DERIVED_CONFIGURATION', 'AUXILIARY_NOT_STRATEGY'}
LP_FIELDS = {'vault', 'factory', 'router', 'position_manager', 'pool', 'w0g', 'usdce',
             'token0', 'token1', 'fee_tier', 'tick_spacing', 'tick_lower', 'tick_upper',
             'sqrt_lower_x96', 'sqrt_upper_x96', 'target_usdc_bps', 'router_mode'}
FIELDS = {
    'NATIVE_STAKE_0G': {'initial_owner', 'vault', 'validator'},
    'GIMO_STAKE_0G': {'vault', 'stake_pool', 'st0g', 'referral'},
    'JAINE_LP_0G_USDC': LP_FIELDS,
    'OKU_LP_0G_USDC': LP_FIELDS,
    'ASCEND_STAKE_A0G': {'vault', 'source_core', 'w0g', 'a0g', 'withdrawal_queue',
                        'source_asset', 'queue_asset', 'queue_source_core'},
}
INTEGER_FIELDS = {'fee_tier', 'tick_spacing', 'tick_lower', 'tick_upper',
                  'sqrt_lower_x96', 'sqrt_upper_x96', 'target_usdc_bps'}


def address(value):
    if not isinstance(value, str) or not re.fullmatch(r'0x[0-9a-fA-F]{40}', value) or int(value, 16) == 0:
        raise ValueError('nonzero address required')
    return value.lower()


def validate_route_parameters(strategy_id, chain_id, parameters, *, evidence_label):
    """Validate explicit hypothetical values, without qualifying any capture.

    Caller assertions of pool/queue properties are NOT authenticated state.
    No fingerprint, RuntimeConfigContext, VERIFIED record or admission is emitted.
    """
    if strategy_id not in FIELDS:
        raise ValueError('not one of five strategy architectures')
    if type(chain_id) is not int or chain_id != 16661:
        raise ValueError('intended execution chain must be 16661')
    if evidence_label != 'SYNTHETIC_PREFLIGHT_ONLY':
        raise ValueError('explicit SYNTHETIC_PREFLIGHT_ONLY label required')
    if set(parameters) != FIELDS[strategy_id] or any(v is None for v in parameters.values()):
        raise ValueError('complete supplied structural parameters required; unresolved is not valid')
    p = dict(parameters)
    for k, v in p.items():
        if k in INTEGER_FIELDS:
            if type(v) is not int:
                raise ValueError('integer field required')
        elif k == 'referral':
            if not isinstance(v, str):
                raise ValueError('referral must be a string; empty is allowed')
        elif k != 'router_mode':
            p[k] = address(v)
    if strategy_id in {'JAINE_LP_0G_USDC', 'OKU_LP_0G_USDC'}:
        if {p['token0'], p['token1']} != {p['w0g'], p['usdce']} or p['token0'] == p['token1']:
            raise ValueError('LP pair/token ordering inconsistent')
        if int(p['token0'], 16) >= int(p['token1'], 16):
            raise ValueError('canonical V3 token ordering must be ascending')
        if not 0 < p['fee_tier'] < 2**24 or not 0 < p['tick_spacing'] < 2**23:
            raise ValueError('invalid fee/tick spacing')
        if not -887272 <= p['tick_lower'] < p['tick_upper'] <= 887272:
            raise ValueError('invalid tick range')
        if p['tick_lower'] % p['tick_spacing'] or p['tick_upper'] % p['tick_spacing']:
            raise ValueError('tick range is not spacing aligned')
        if not 0 < p['sqrt_lower_x96'] < p['sqrt_upper_x96'] < 2**160:
            raise ValueError('invalid sqrt bounds')
        if not 0 < p['target_usdc_bps'] < 10000:
            raise ValueError('invalid target bps')
        mode = 'V1' if strategy_id == 'JAINE_LP_0G_USDC' else 'ROUTER02'
        if p['router_mode'] != mode:
            raise ValueError('wrong router ABI mode')
    if strategy_id == 'ASCEND_STAKE_A0G':
        if p['source_core'] != p['a0g'] or p['queue_source_core'] != p['source_core']:
            raise ValueError('SourceCore/share/queue relationship inconsistent')
        if p['source_asset'] != p['w0g'] or p['queue_asset'] != p['w0g']:
            raise ValueError('SourceCore/queue assets must be W0G')
    return {'strategy_id': strategy_id, 'execution_chain_id': chain_id,
            'parameter_check': 'STATICALLY_VALIDATED', 'evidence_class': evidence_label,
            'runtime_binding': 'UNRESOLVED_RUNTIME_BINDING', 'public_deployment': 'NOT_DEPLOYED'}


def validate_design(design):
    if design['artifact_type'] != 'INTENDED_DEPLOYMENT_ARCHITECTURE' or design['design_schema_version'] != '1.0':
        raise ValueError('design is not a deployment manifest')
    if design['public_deployment_required'] is not False or design['public_deployment_planned'] is not False:
        raise ValueError('no public deployment required/planned')
    if type(design['execution_chain_id']) is not int or design['execution_chain_id'] != 16661:
        raise ValueError('intended execution chain must be 16661')
    if design['network_roles'] != {'16661': 'INTENDED_EXECUTION_DOMAIN_NOT_DEPLOYMENT_PROOF',
        '1': 'ASCEND_BACKING_DEPENDENCY_ONLY', '16602': 'CONDITIONAL_DEVELOPMENT_TEST_ONLY', '8453': 'KIV_ONLY'}:
        raise ValueError('network-role mixing')
    dependencies = design['dependency_domains']
    if len(dependencies) != 1 or dependencies[0]['strategy_id'] != 'ASCEND_STAKE_A0G' or dependencies[0]['chain_id'] != 1 or dependencies[0]['classification'] != 'EXTERNAL_PROTOCOL_REFERENCE':
        raise ValueError('Ethereum remains Ascend backing dependency only')
    provenance = dependencies[0]['evidence_source']
    if hashlib.sha256((ROOT / provenance['path']).read_bytes()).hexdigest() != provenance['sha256']:
        raise ValueError('dependency reference changed')
    ids = [r['strategy_id'] for r in design['strategies']]
    if len(ids) != 5 or set(ids) != set(STRATEGIES):
        raise ValueError('exactly five independent architectures')
    if design['runtime_readiness'] != 'UNRESOLVED_RUNTIME_BINDING' or design['public_deployment'] != 'NOT_DEPLOYED':
        raise ValueError('no public deployment/readiness proof')
    if {r['component'] for r in design['core']} != {'StrategyManager', 'AscendVault', 'RewardAccounting'}:
        raise ValueError('core topology incomplete')
    actual = json.loads((ROOT / 'data/runtime_strategy_config.json').read_text())
    references = {r['strategy_id']: r['config_components'] for r in actual['records']}
    for row in design['core'] + design['strategies']:
        if 'strategy_id' in row:
            if row['adapter'] != STRATEGIES[row['strategy_id']]:
                raise ValueError('adapter/strategy mismatch')
            expected_gate = 'CLOSED' if row['strategy_id'] == 'ASCEND_STAKE_A0G' else 'CONDITIONAL'
            if row['allocation_gate'] != expected_gate:
                raise ValueError('frozen gate changed')
            if row['readiness']['public_deployment'] != 'NOT_PERFORMED' or row['readiness']['runtime_binding'] != 'RUNTIME_BINDING_UNRESOLVED':
                raise ValueError('local simulation cannot prove public deployment')
        elif row['public_deployment'] != 'NOT_PERFORMED':
            raise ValueError('no public core deployment proof')
        names = [c['component'] for c in row['components']]
        if len(names) != len(set(names)):
            raise ValueError('duplicate component')
        for c in row['components']:
            if 'strategy_id' in row and c['component'] in references[row['strategy_id']]:
                expected = references[row['strategy_id']][c['component']]
                if c['value'] != expected:
                    raise ValueError('design reference/unresolved input differs from frozen source metadata')
            if c['classification'] not in CLASSES:
                raise ValueError('unknown component classification')
            if c['chain_id'] != 16661:
                raise ValueError('route component from different chain')
            if c['classification'] == 'UNRESOLVED_DEPLOYMENT_INPUT' and c['value'] is not None:
                raise ValueError('unresolved input must remain null')
            s = c['evidence_source']
            if hashlib.sha256((ROOT / s['path']).read_bytes()).hexdigest() != s['sha256']:
                raise ValueError('source changed; design needs reconciliation')
            if c['classification'] == 'EXTERNAL_PROTOCOL_REFERENCE':
                address(c['value'])
                if c['value'].lower() not in (ROOT / s['path']).read_text().lower():
                    raise ValueError('protocol reference is not in cited source')
            if c['component'] == 'router_mode':
                expected = 'V1' if row['strategy_id'] == 'JAINE_LP_0G_USDC' else 'ROUTER02'
                if c['value'] != expected:
                    raise ValueError('wrong router ABI mode')
    for path, digest in design['unchanged_files'].items():
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != digest:
            raise ValueError('frozen file changed: ' + path)
    return {'architecture': 'INTENDED_DEPLOYMENT_ARCHITECTURE', 'source_structure': 'STATICALLY_VALIDATED',
            'strategy_count': 5, 'execution_chain_id': 16661, 'runtime_binding': 'UNRESOLVED_RUNTIME_BINDING',
            'public_deployment': 'NOT_DEPLOYED', 'public_deployment_required': False}


if __name__ == '__main__':
    # Read-only local file operation; no RPC or transaction command exists.
    result = validate_design(json.loads(DESIGN_PATH.read_text()))
    print(json.dumps(result, indent=2))
