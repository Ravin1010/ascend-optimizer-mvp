"""Exit-stage/time-to-native-0G primitive; not execution or deadline approval."""
from __future__ import annotations
from dataclasses import dataclass
import json
from pathlib import Path

from .data_loader import DEFAULT_DATA_DIR
from .risk_stress import LABEL, STRATEGIES, NATIVE, GIMO, JAINE, OKU, ASCEND, decimal, fingerprint, precision, RiskError
from .lp_range_stress import text

VERSION='EXIT_LIQUIDITY_V1'
CONFIG_VERSION='EXIT_EVALUATION_V1'
PATHS={
 NATIVE: ('ASYNCHRONOUS','Validator undelegation request','Unbonding/maturity','Validator withdraw processing and adapter claim; native 0G', 'contracts/adapters/Native0GStakingAdapter.sol'),
 GIMO: ('ASYNCHRONOUS','st0G unstake/request','Pending maturity period','stakePool.withdraw and serialized adapter claim; native 0G','contracts/adapters/GimoAdapter.sol'),
 JAINE: ('SYNCHRONOUS','Remove LP liquidity and swap residual USDC.e to W0G','No protocol waiting period','Unwrap W0G and transfer native 0G in synchronous unwind','contracts/adapters/JaineLPAdapter.sol'),
 OKU: ('SYNCHRONOUS','Remove LP liquidity and Router02 swap residual USDC.e to W0G','No protocol waiting period','Unwrap W0G and transfer native 0G in synchronous unwind','contracts/adapters/V3LiquidityAdapter.sol'),
 ASCEND: ('QUEUE_BASED','SourceCore requestWithdrawal','Epoch/queue maturity then funding','Claim epoch W0G, unwrap and settle native 0G','contracts/adapters/AscendProtocolAdapter.sol'),
}
DURATIONS=('request_processing_days','waiting_maturity_days','funding_wait_days','claim_processing_days')
FIELDS={'config_id','strategy_id','version','label','evidence_class','assumptions'} | set(DURATIONS)


@dataclass(frozen=True)
class ExitResult:
    strategy_id: str
    exit_model_version: str
    exit_type: str
    requestable_now_state: str
    request_step: str
    waiting_step: str
    claim_step: str
    waiting_maturity_days: str | None
    request_processing_days: str | None
    funding_wait_days: str | None
    claim_processing_days: str | None
    time_to_cash_days: str | None
    maturity_state: str
    funding_state: str
    claimability_state: str
    output_asset: str
    evidence_class: str
    timing_evidence_class: str
    qualification_state: str
    holding_horizon_days: str | None
    config_id: str | None
    config_fingerprint: str | None
    provenance: tuple[str,...]
    assumptions: tuple[str,...]
    reasons: tuple[str,...]
    mode: str
    quote_validity: str = 'NOT_ASSESSED_SEPARATE_ITERATION19_BOUNDARY'
    execution_readiness: str = 'NOT_ESTABLISHED'
    allocation_gate: str = 'NOT_EVALUATED_BY_EXIT_MODEL'


def validate_config(c: dict) -> dict:
    if not isinstance(c,dict) or set(c)!=FIELDS or c['strategy_id'] not in STRATEGIES:
        raise RiskError('exit configuration fields/strategy mismatch')
    if c['version']!=CONFIG_VERSION or c['config_id']!=CONFIG_VERSION+':'+c['strategy_id']:
        raise RiskError('exit config identity/version mismatch')
    if c['label']!=LABEL or c['evidence_class']!='MODELLED':
        raise RiskError('synthetic exit assumptions must remain modelled')
    if not isinstance(c['assumptions'],list) or not c['assumptions'] or any(not isinstance(s,str) or not s for s in c['assumptions']):
        raise RiskError('exit provenance/assumptions required')
    for k in DURATIONS:
        if c[k] is not None:
            decimal(c[k])
    # Protocol-level synchronous means no maturity or funding queue, not no latency.
    if c['strategy_id'] in (JAINE,OKU) and (c['waiting_maturity_days']!='0' or c['funding_wait_days']!='0'):
        raise RiskError('synchronous LP path cannot acquire a protocol queue')
    return c


def load_configs(path=DEFAULT_DATA_DIR/'exit_evaluation_config.json') -> list[dict]:
    d=json.loads(Path(path).read_text())
    if set(d)!= {'version','artifact_type','label','configurations'} or d['version']!=CONFIG_VERSION or d['artifact_type']!='SYNTHETIC_EVALUATION_CONFIGURATION' or d['label']!=LABEL:
        raise RiskError('synthetic exit artifact required')
    rows=[validate_config(c) for c in d['configurations']]
    if len(rows)!=5 or {c['strategy_id'] for c in rows}!=set(STRATEGIES):
        raise RiskError('exact five exit configurations required')
    return rows


def assess(strategy_id: str, *, mode='PRODUCTION', config=None, holding_horizon_days=None) -> ExitResult:
    if strategy_id not in STRATEGIES or mode not in ('PRODUCTION',LABEL):
        raise RiskError('unknown strategy/exit mode')
    if holding_horizon_days is not None:
        decimal(holding_horizon_days,positive=True)
    exit_type,request,wait,claim,source=PATHS[strategy_id]
    assumptions=[];reasons=['Time-to-cash starts at exit decision; holding horizon is separate',
                           'Does not establish quote feasibility, technical admission or public deployment']
    if config is not None:
        if mode!=LABEL:
            raise RiskError('modelled duration requires explicit synthetic mode')
        validate_config(config)
        if config['strategy_id']!=strategy_id:
            raise RiskError('exit strategy/config mismatch')
        durations={k:config[k] for k in DURATIONS}
        with precision():
            total=None if any(v is None for v in durations.values()) else text(sum(decimal(v) for v in durations.values()))
        timing='MODELLED' if total is not None else 'MISSING'
        qualification='ASSESSED_MODELLED' if total is not None else 'UNRESOLVED'
        requestable='ASSUMED_REQUESTABLE_FOR_EVALUATION'
        maturity='ASSUMED_MATURE_AFTER_WAIT' if durations['waiting_maturity_days'] is not None else 'UNRESOLVED'
        funding='ASSUMED_FUNDED_AFTER_WAIT' if durations['funding_wait_days'] is not None else 'UNRESOLVED'
        claimability='CONDITIONAL_ON_REQUEST_MATURITY_FUNDING_AND_EXECUTION'
        assumptions=config['assumptions']
        config_id=config['config_id'];config_hash=fingerprint(config)
        evidence='MODELLED'
    else:
        # Source-level synchronous path establishes only no protocol wait, not
        # actual requestability, transaction latency or usable executable quote.
        synchronous=exit_type=='SYNCHRONOUS'
        durations={k:('0' if synchronous and k in ('waiting_maturity_days','funding_wait_days') else None) for k in DURATIONS}
        total=None;timing='MISSING';qualification='PARTIALLY_ASSESSED' if synchronous else 'UNRESOLVED'
        requestable=maturity=funding=claimability='UNRESOLVED'
        config_id=config_hash=None;evidence='STATIC_CONFIG'  # Source path only; not timing evidence.
        assumptions=['Source-fixed adapter flow; no configured/deployed route or current position state',
                     'No authoritative current duration/requestability/funding evidence supplied']
        if synchronous:
            reasons.append('Synchronous protocol operation is not guaranteed successful execution or instant cash')
    if total is None:
        reasons.append('UNRESOLVED_TIME_TO_CASH; missing duration is not zero')
    if strategy_id==GIMO:
        reasons.append('Adapter serializes one outstanding protocol withdrawal; current busy state unresolved')
    if strategy_id==NATIVE:
        reasons.append('Validator binding, maturity state and withdrawal-fee reserve unresolved')
    if strategy_id==ASCEND:
        reasons.append('Ascend CLOSED; epoch maturity, funding and claimability are separate, unresolved at runtime')
    return ExitResult(strategy_id,VERSION,exit_type,requestable,request,wait,claim,
                      durations['waiting_maturity_days'],durations['request_processing_days'],durations['funding_wait_days'],durations['claim_processing_days'],total,
                      maturity,funding,claimability,'native 0G',evidence,timing,qualification,holding_horizon_days,
                      config_id,config_hash,(source,),tuple(assumptions),tuple(reasons),mode,
                      allocation_gate='CLOSED' if strategy_id==ASCEND else 'NOT_EVALUATED_BY_EXIT_MODEL')


def deadline_compatible(result: ExitResult, deadline_days: str) -> str:
    """Analysis-only tri-state helper; no optimizer input/ranking integration."""
    deadline=decimal(deadline_days)
    if result.time_to_cash_days is None:
        return 'UNRESOLVED'
    return 'COMPATIBLE_MODELLED' if decimal(result.time_to_cash_days)<=deadline else 'INCOMPATIBLE_MODELLED'
