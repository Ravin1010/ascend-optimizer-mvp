"""Canonical actual-route configuration; independent of admission/market data.

Verification is an explicit evidence-backed assertion, never inferred from a
fingerprint. No RPC, market discovery, headroom or wall clock is used here.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

from .admission_records import timestamp_value
from .admission_validity import RuntimeConfigContext
from .data_loader import DEFAULT_DATA_DIR, MVP_STRATEGY_IDS, SchemaValidationError

DEFAULT_RUNTIME_CONFIG_PATH = DEFAULT_DATA_DIR / 'runtime_strategy_config.json'
IDENTITY_VERSION = 'RUNTIME_ROUTE_V1'
COMMON = ('adapter_address', 'vault_address', 'strategy_manager_address', 'manager_strategy_key', 'adapter_class')
LP_FIELDS = ('factory', 'router', 'position_manager', 'pool', 'w0g', 'usdce', 'token0', 'token1',
             'fee_tier', 'tick_spacing', 'tick_lower', 'tick_upper', 'sqrt_lower_x96', 'sqrt_upper_x96',
             'target_usdc_bps', 'router_mode')
ROUTE_FIELDS = {
    'NATIVE_STAKE_0G': COMMON + ('validator',),
    'GIMO_STAKE_0G': COMMON + ('stake_pool', 'st0g', 'withdrawal_contract', 'referral'),
    'JAINE_LP_0G_USDC': COMMON + LP_FIELDS,
    'OKU_LP_0G_USDC': COMMON + LP_FIELDS,
    'ASCEND_STAKE_A0G': COMMON + ('w0g', 'source_core', 'a0g', 'withdrawal_queue'),
}
ADDRESS_FIELDS = frozenset({'adapter_address', 'vault_address', 'strategy_manager_address', 'validator',
    'stake_pool', 'st0g', 'withdrawal_contract', 'factory', 'router', 'position_manager', 'pool',
    'w0g', 'usdce', 'token0', 'token1', 'source_core', 'a0g', 'withdrawal_queue'})
INTEGER_FIELDS = frozenset({'fee_tier', 'tick_spacing', 'tick_lower', 'tick_upper',
                          'sqrt_lower_x96', 'sqrt_upper_x96', 'target_usdc_bps'})
RECORD_FIELDS = frozenset({'strategy_id', 'execution_chain_id', 'verification_state', 'verification_source',
    'verified_at', 'block_number', 'block_hash', 'config_identity', 'config_components', 'evidence_sources',
    'verification_notes'})
PROOF_TYPES = frozenset({'DEPLOYMENT_ARTIFACT', 'ONCHAIN_READ', 'VERIFIED_EXPLORER'})


def _error(message):
    raise SchemaValidationError('runtime config: ' + message)


def normalize_components(strategy_id: str, components: dict, *, complete: bool = True) -> dict:
    if not isinstance(strategy_id,str) or strategy_id not in ROUTE_FIELDS or not isinstance(components, dict):
        _error('unknown strategy or malformed components')
    expected = set(ROUTE_FIELDS[strategy_id])
    if set(components) != expected:
        _error('component keys must exactly match route specification')
    normalized = {}
    for key in sorted(expected):
        value = components[key]
        if value is None:
            if complete:
                _error('missing required component: ' + key)
            normalized[key] = None
            continue
        if key in ADDRESS_FIELDS:
            if not isinstance(value, str) or not re.fullmatch(r'0x[0-9a-fA-F]{40}', value) or int(value,16) == 0:
                _error('invalid contract address: ' + key)
            value = value.lower()
        elif key == 'manager_strategy_key':
            if not isinstance(value,str) or not re.fullmatch(r'0x[0-9a-fA-F]{64}',value) or int(value,16)==0:
                _error('invalid registration key')
            value=value.lower()
        elif key in INTEGER_FIELDS:
            if type(value) is not int:
                _error('integer component required: ' + key)
        elif not isinstance(value, str) or (key != 'referral' and not value):
            _error('text component required: ' + key)
        normalized[key] = value
    if complete and strategy_id in {'JAINE_LP_0G_USDC','OKU_LP_0G_USDC'}:
        n=normalized
        if {n['token0'],n['token1']} != {n['w0g'],n['usdce']} or n['token0'] == n['token1']:
            _error('LP token ordering/roles inconsistent')
        if not 0 < n['fee_tier'] < 2**24 or n['tick_spacing'] <= 0:
            _error('invalid fee or tick spacing')
        if not -887272 <= n['tick_lower'] < n['tick_upper'] <= 887272:
            _error('invalid LP range')
        if n['tick_lower'] % n['tick_spacing'] or n['tick_upper'] % n['tick_spacing']:
            _error('range not tick-spacing aligned')
        if not 0 < n['sqrt_lower_x96'] < n['sqrt_upper_x96'] < 2**160 or not 0 < n['target_usdc_bps'] < 10000:
            _error('invalid sqrt bounds or target')
        expected_mode='V1' if strategy_id=='JAINE_LP_0G_USDC' else 'ROUTER02'
        if n['router_mode'] != expected_mode:
            _error('router ABI does not match strategy')
    return normalized


def canonical_serialization(strategy_id: str, execution_chain_id: int, components: dict) -> str:
    if type(execution_chain_id) is not int or execution_chain_id <= 0:
        _error('positive integer chain required')
    return json.dumps({'identity_version': IDENTITY_VERSION, 'strategy_id': strategy_id,
        'execution_chain_id': execution_chain_id,
        'config_components': normalize_components(strategy_id,components)},
        sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)


def config_fingerprint(strategy_id: str, execution_chain_id: int, components: dict) -> str:
    payload=canonical_serialization(strategy_id,execution_chain_id,components).encode('utf-8')
    return 'sha256:' + hashlib.sha256(payload).hexdigest()


def _no_duplicate_keys(pairs):
    out={}
    for key,value in pairs:
        if key in out: _error('duplicate JSON key: '+key)
        out[key]=value
    return out


def load_runtime_configs(path: str | Path = DEFAULT_RUNTIME_CONFIG_PATH) -> tuple[dict,...]:
    try:
        data=json.loads(Path(path).read_text(),object_pairs_hook=_no_duplicate_keys)
    except (OSError,ValueError) as exc:
        _error('unusable dataset: '+str(exc))
    if not isinstance(data,dict) or set(data)!={'schema_version','identity_version','records'} or data['schema_version']!='1.0' or data['identity_version']!=IDENTITY_VERSION:
        _error('unsupported dataset schema')
    rows=data['records']
    if not isinstance(rows,list): _error('records must be a list')
    ids=[]
    for row in rows:
        if not isinstance(row,dict) or set(row)!=RECORD_FIELDS: _error('invalid record fields')
        sid=row['strategy_id'];ids.append(sid)
        if not isinstance(sid,str) or sid not in MVP_STRATEGY_IDS: _error('unknown independent strategy')
        if type(row['execution_chain_id']) is not int or row['execution_chain_id'] != 16661:
            _error('current route must be 0G Mainnet 16661')
        state=row['verification_state']
        if not isinstance(state,str) or state not in {'VERIFIED','UNRESOLVED'}: _error('invalid verification state')
        row['config_components']=normalize_components(sid,row['config_components'],complete=state=='VERIFIED')
        if not isinstance(row['evidence_sources'],list) or not row['evidence_sources']:
            _error('audit provenance required, including unresolved records')
        for source in row['evidence_sources']:
            if not isinstance(source,dict) or any(not isinstance(source.get(k),str) or not source[k]
                                                  for k in ('source_id','location','source_type')):
                _error('source identity/location/type required')
            for key in ('verified_components','code_verified_addresses'):
                values=source.get(key,[])
                if not isinstance(values,list) or any(not isinstance(v,str) for v in values):
                    _error('proof coverage/code addresses must be string lists')
            if any(not re.fullmatch(r'0x[0-9a-fA-F]{40}',a) for a in source.get('code_verified_addresses',[])):
                _error('malformed proof contract address')
        if not isinstance(row['verification_notes'],str) or not row['verification_notes']:
            _error('verification/resolution notes required')
        block=row['block_number'];block_hash=row['block_hash']
        if block is not None and (type(block) is not int or block<0): _error('invalid block number')
        if block_hash is not None and (not isinstance(block_hash,str) or not re.fullmatch(r'0x[0-9a-fA-F]{64}',block_hash)):
            _error('invalid block hash')
        if state=='UNRESOLVED':
            if row['config_identity'] is not None or row['verified_at'] is not None or row['verification_source'] is not None:
                _error('unresolved record must not fabricate identity or verification')
            continue
        if not isinstance(row['verification_source'],str) or not row['verification_source'] or not isinstance(row['verified_at'],str) or not row['verified_at']:
            _error('verified source/time required')
        timestamp_value(row['verified_at'],'verified_at')
        if row['config_identity'] != config_fingerprint(sid,row['execution_chain_id'],row['config_components']):
            _error('fingerprint differs from canonical components')
        proofs=[s for s in row['evidence_sources'] if s['source_type'] in PROOF_TYPES]
        if row['verification_source'] not in {s['source_id'] for s in proofs}:
            _error('verification source must reference deployment/on-chain/explorer proof')
        covered=set().union(*(set(s.get('verified_components',[])) for s in proofs))
        if not set(ROUTE_FIELDS[sid]).union({'execution_chain_id','strategy_id'}) <= covered:
            _error('proof must cover actual registration and every route component')
        addresses={row['config_components'][k] for k in ADDRESS_FIELDS.intersection(row['config_components'])}
        checked=set().union(*(set(a.lower() for a in s.get('code_verified_addresses',[])) for s in proofs))
        if not addresses <= checked: _error('contract-code proof required for route addresses')
        if any(s.get('chain_id') != row['execution_chain_id'] for s in proofs):
            _error('proof chain mismatch')
    if len(ids)!=len(set(ids)) or set(ids)!=MVP_STRATEGY_IDS:
        _error('exactly five unique structural configuration records required')
    return tuple(rows)


def runtime_config_contexts(path: str | Path = DEFAULT_RUNTIME_CONFIG_PATH) -> dict[str,RuntimeConfigContext]:
    return {r['strategy_id']:RuntimeConfigContext(r['strategy_id'],r['execution_chain_id'],
        r['config_identity'] or '',r['verification_state'],r['verification_source'])
        for r in load_runtime_configs(path)}
