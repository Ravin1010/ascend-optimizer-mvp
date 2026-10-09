"""Deterministic capture validity; operational policy, not protocol guarantees."""
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal, localcontext
from enum import Enum
from typing import Mapping

from .admission_records import AdmissionRecord, SOURCE_ROLES, timestamp_value

POLICY_VERSION = 'ADMISSION_VALIDITY_V1'

class ValidityState(str, Enum):
    VALID = 'VALID'
    STALE = 'STALE'
    CONFIG_MISMATCH = 'CONFIG_MISMATCH'
    AMOUNT_MISMATCH = 'AMOUNT_MISMATCH'
    SOURCE_UNVERIFIED = 'SOURCE_UNVERIFIED'
    MISSING = 'MISSING'
    POLICY_UNDEFINED = 'POLICY_UNDEFINED'

@dataclass(frozen=True)
class FreshnessPolicy:
    max_age_seconds: int
    production_usable: bool
    rationale: str

    def __post_init__(self):
        if type(self.max_age_seconds) is not int or self.max_age_seconds < 0:
            raise ValueError('max_age_seconds must be a non-negative integer')
        if type(self.production_usable) is not bool or not self.rationale:
            raise ValueError('policy requires boolean production_usable and rationale')

# Five minutes is a deliberately short decision-to-execution operational budget,
# not empirical source stability. Static admission claims lack a mechanism that
# distinguishes immutable permission from dynamic remaining headroom: undefined.
DEFAULT_POLICIES = {
    (role, evidence_class, evidence_type): FreshnessPolicy(
        300, evidence_class != 'MODELLED',
        'Short operational admission budget; no guarantee of stable headroom')
    for role in set(SOURCE_ROLES.values())
    for evidence_class in ('LIVE_OBSERVED', 'LIVE_DERIVED', 'MODELLED')
    for evidence_type in ('EXACT_POINT', 'SCALAR_BOUND')
}

@dataclass(frozen=True)
class RuntimeConfigContext:
    strategy_id: str
    chain_id: int
    config_identity: str
    verification_state: str = 'UNRESOLVED'
    verification_source: str | None = None

@dataclass(frozen=True)
class ValidityAssessment:
    state: ValidityState
    as_of: str
    observation_timestamp: str | None
    retrieval_timestamp: str | None
    observation_age_seconds: float | None
    max_age_seconds: int | None
    source_role: str
    evidence_class: str
    config_identity: str | None
    candidate_amount_0g: str
    candidate_amount_usd: str
    policy_version: str
    reason_code: str
    details: str
    config_verification_state: str | None
    config_verification_source: str | None

    def to_dict(self):
        return asdict(self)


def require_as_of(as_of: datetime) -> datetime:
    if not isinstance(as_of, datetime) or as_of.utcoffset() is None:
        raise ValueError('explicit timezone-aware as_of required')
    return as_of


def assess_capture(record: AdmissionRecord, *, as_of: datetime, amount: Decimal,
                   usd: Decimal, context: RuntimeConfigContext | None,
                   allow_modelled: bool = False,
                   policies: Mapping = DEFAULT_POLICIES) -> ValidityAssessment:
    require_as_of(as_of)
    observation = timestamp_value(record.get('observation_timestamp'), 'observation_timestamp')
    age = None if observation is None else (as_of - observation).total_seconds()
    policy = policies.get((record.get('source_role'), record.get('evidence_class'), record.get('evidence_type')))
    def result(state, reason):
        return ValidityAssessment(state, as_of.isoformat(), record.get('observation_timestamp') or None,
            record.get('retrieval_timestamp') or None, age, None if policy is None else policy.max_age_seconds,
            record.get('source_role'), record.get('evidence_class'), record.get('config_identity') or None,
            str(amount), str(usd), POLICY_VERSION, reason, reason,
            None if context is None else context.verification_state,
            None if context is None else context.verification_source)
    capture = record.get('capture_status')
    if capture == 'SOURCE_UNVERIFIED':
        return result(ValidityState.SOURCE_UNVERIFIED, 'CAPTURE_SOURCE_UNVERIFIED')
    if capture == 'CONFIG_UNRESOLVED':
        return result(ValidityState.CONFIG_MISMATCH, 'EVIDENCE_CONFIG_UNRESOLVED')
    if capture != 'CAPTURED' or observation is None or not record.get('retrieval_timestamp'):
        return result(ValidityState.MISSING, 'REQUIRED_CAPTURE_UNAVAILABLE')
    if not record.get('config_identity') or context is None or not context.config_identity:
        return result(ValidityState.MISSING, 'CONFIG_CONTEXT_MISSING')
    if context.strategy_id != record.get('strategy_id') or context.chain_id != int(record.get('chain_id')) or context.config_identity != record.get('config_identity'):
        return result(ValidityState.CONFIG_MISMATCH, 'CONFIG_CONTEXT_MISMATCH')
    if context.verification_state != 'VERIFIED' or not context.verification_source:
        return result(ValidityState.SOURCE_UNVERIFIED, 'RUNTIME_CONFIG_NOT_VERIFIED')
    if age < 0:
        return result(ValidityState.MISSING, 'FUTURE_OBSERVATION')
    if record.get('evidence_type') == 'EXACT_POINT' and amount != record.number('amount_0g'):
        return result(ValidityState.AMOUNT_MISMATCH, 'EXACT_AMOUNT_MISMATCH')
    usd_dependent = any(record.number(field) is not None for field in
                        ('amount_usd', 'tested_amount_usd', 'scalar_headroom_usd'))
    if usd_dependent:
        price = record.number('valuation_price_usd')
        with localcontext() as decimal_context:
            decimal_context.prec = max(28, len(amount.as_tuple().digits) + len(price.as_tuple().digits))
            expected_usd = amount * price
        if usd != expected_usd:
            return result(ValidityState.AMOUNT_MISMATCH, 'VALUATION_CONTEXT_MISMATCH')
    if record.get('evidence_class') == 'HISTORICAL' or (record.get('evidence_class') == 'MODELLED' and not allow_modelled):
        return result(ValidityState.SOURCE_UNVERIFIED, 'EVIDENCE_CLASS_NOT_PRODUCTION_ADMISSION')
    if policy is None:
        return result(ValidityState.POLICY_UNDEFINED, 'NO_VALID_POLICY')
    if not policy.production_usable and not (allow_modelled and record.get('evidence_class') == 'MODELLED'):
        return result(ValidityState.SOURCE_UNVERIFIED, 'POLICY_NOT_PRODUCTION_USABLE')
    if age > policy.max_age_seconds:
        return result(ValidityState.STALE, 'OBSERVATION_EXPIRED')
    return result(ValidityState.VALID, 'CAPTURE_VALID_UNDER_OPERATIONAL_POLICY')
