"""Repository-only technical admission. Explicit capture freshness/config validity; no RPC, TVL or quote fallback."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Mapping

from .admission_records import DEFAULT_ADMISSION_PATH, load_admission_records, timestamp_value
from .amount_optimizer import AdmissionEvidence, AdmissionState
from .data_loader import SchemaValidationError
from .strategy_state import strategy_state
from .admission_validity import (DEFAULT_POLICIES, RuntimeConfigContext, ValidityState,
                                 assess_capture, require_as_of)


class RepositoryAdmissionProvider:
    def __init__(self, path: str | Path = DEFAULT_ADMISSION_PATH, *, strategies=None,
                 config_identities: Mapping[str, str] | None = None, allow_modelled: bool = False,
                 config_contexts: Mapping[str, RuntimeConfigContext] | None = None,
                 as_of: datetime | None = None, policies: Mapping = DEFAULT_POLICIES,
                 runtime_config_path: str | Path | None = None):
        if not isinstance(allow_modelled, bool):
            raise ValueError("allow_modelled must be an explicit boolean demo/test opt-in")
        self.path = Path(path)
        self.strategies = strategies
        # Explicit caller or canonical repository context; never infer from notes/reference IDs.
        self.config_identities = dict(config_identities or {})
        self.allow_modelled = allow_modelled
        from .runtime_config import DEFAULT_RUNTIME_CONFIG_PATH
        self.runtime_config_path = (Path(runtime_config_path) if runtime_config_path is not None else
            DEFAULT_RUNTIME_CONFIG_PATH if config_contexts is None and config_identities is None else None)
        if runtime_config_path is not None and (config_contexts is not None or config_identities is not None):
            raise ValueError('repository config path and explicit context overrides are mutually exclusive')
        self.config_contexts = dict(config_contexts or {})
        if any(not isinstance(c, RuntimeConfigContext) for c in self.config_contexts.values()):
            raise ValueError('typed RuntimeConfigContext required')
        self.as_of = as_of
        self.policies = dict(policies)

    def __call__(self, *, strategy, amount_0g: float, amount_usd: float,
                 canonical_amount_0g: Decimal | None = None,
                 canonical_amount_usd: Decimal | None = None, as_of: datetime | None = None, **kwargs) -> AdmissionEvidence:
        evaluation_time = require_as_of(self.as_of if as_of is None else as_of)
        assessments = []
        sid, chain = str(strategy.strategy_id), int(strategy.execution_chain_id)
        def unknown(*diagnostics):
            ordered = sorted(assessments, key=lambda a: a['evidence_id'])
            validity = ordered[0] if ordered else {
                'state': 'MISSING', 'as_of': evaluation_time.isoformat(),
                'observation_timestamp': None, 'retrieval_timestamp': None,
                'observation_age_seconds': None, 'max_age_seconds': None,
                'source_role': '', 'evidence_class': 'MISSING/UNRESOLVED',
                'config_identity': None, 'candidate_amount_0g': str(amount_0g if canonical_amount_0g is None else canonical_amount_0g),
                'candidate_amount_usd': str(amount_usd if canonical_amount_usd is None else canonical_amount_usd), 'policy_version': 'ADMISSION_VALIDITY_V1',
                'reason_code': 'NO_USABLE_CAPTURE', 'details': 'No usable matching capture',
                'config_verification_state': None, 'config_verification_source': None}
            if any(d.startswith('CONFLICTING_CAPTURE_STATUSES') for d in diagnostics):
                validity = dict(validity, state='SOURCE_UNVERIFIED', reason_code='CONFLICTING_CAPTURE_STATUSES',
                                details='Individually valid captures disagree; admission fails closed')
            return AdmissionEvidence(AdmissionState.UNKNOWN, sid, amount_0g, chain, "UNAVAILABLE",
                                     "No usable repository admission capture", "MISSING/UNRESOLVED",
                                     diagnostics=tuple(diagnostics), validity=validity,
                                     validity_records=tuple(ordered))
        if not strategy_state(strategy).allocation_admitted:
            return unknown("METADATA_GATE_NOT_ADMITTED")
        contexts = self.config_contexts
        if self.runtime_config_path is not None:
            from .runtime_config import runtime_config_contexts
            try:
                contexts = runtime_config_contexts(self.runtime_config_path)
            except SchemaValidationError as exc:
                return unknown('CONFIG_DATASET_UNUSABLE: ' + str(exc))
        # Reload on every candidate and revalidation lookup. Withdrawal/change is
        # visible; no cache makes an old capture survive a removed/replaced file.
        try:
            records = load_admission_records(self.path, strategies=self.strategies)
        except (OSError, SchemaValidationError) as exc:
            return unknown("EVIDENCE_DATASET_UNUSABLE: " + str(exc))
        # The optimizer supplies identity derived from original decimal inputs,
        # not Decimal(str(binary-float multiplication)). Direct callers retain
        # exact semantics for their supplied decimal representations.
        amount = Decimal(str(amount_0g)) if canonical_amount_0g is None else canonical_amount_0g
        usd = Decimal(str(amount_usd)) if canonical_amount_usd is None else canonical_amount_usd
        if not isinstance(amount, Decimal) or not isinstance(usd, Decimal):
            return unknown("INVALID_CANONICAL_CANDIDATE_AMOUNT")
        if not amount.is_finite() or amount <= 0 or not usd.is_finite() or usd <= 0:
            return unknown("INVALID_CANDIDATE_AMOUNT")
        matched, diagnostics = [], []
        for record in records:
            if record.get("strategy_id") != sid or int(record.get("chain_id")) != chain:
                continue
            identity = record.get("evidence_id")
            context = contexts.get(sid)
            # Legacy identity strings are retained but never certify verification.
            legacy_identity = self.config_identities.get(sid)
            if legacy_identity is not None and (context is None or legacy_identity != context.config_identity):
                context = RuntimeConfigContext(sid, chain, legacy_identity)
            assessment = assess_capture(record, as_of=evaluation_time, amount=amount, usd=usd,
                context=context, allow_modelled=self.allow_modelled, policies=self.policies)
            if assessment.state != ValidityState.VALID:
                assessments.append(dict(assessment.to_dict(), evidence_id=identity,
                                        captured_assertion=record.get('admission_status')))
                diagnostics.append(identity + ':' + assessment.state.value + ':' + assessment.reason_code)
                continue
            status = record.get("admission_status")
            if record.get("evidence_type") == "EXACT_POINT":
                if amount != record.number("amount_0g"):
                    continue
            else:
                bound = record.number("scalar_headroom_0g")
                # Compare USD-only bounds in their own unit; division could
                # create a rounded decimal boundary for non-terminating ratios.
                above_bound = (usd > record.number("scalar_headroom_usd")
                               if bound is None else amount > bound)
                if above_bound:
                    if status == "SUPPORTED":
                        status = "UNSUPPORTED"  # explicit maximum exceeded
                    else:
                        continue  # an unsupported in-bound region says nothing above it
            assessments.append(dict(assessment.to_dict(), evidence_id=identity,
                                    captured_assertion=record.get('admission_status')))
            matched.append((record, status))
        if not matched:
            return unknown(*(diagnostics or ["NO_MATCHING_CAPTURE"]))
        # Never use specificity/recency to silently override a contradictory claim.
        if len({status for _, status in matched}) > 1:
            return unknown(*diagnostics, "CONFLICTING_CAPTURE_STATUSES: " + ",".join(sorted(r.get("evidence_id") for r, _ in matched)))
        # No universal class ranking: agreement -> point specificity, observation
        # time, then stable ID. Retrieval time never substitutes for observation.
        exact = [item for item in matched if item[0].get("evidence_type") == "EXACT_POINT"]
        choices = exact or matched
        newest = max(timestamp_value(r.get("observation_timestamp"), "observation_timestamp") for r, _ in choices)
        record, status = min((item for item in choices if timestamp_value(item[0].get("observation_timestamp"), "observation_timestamp") == newest),
                             key=lambda item: item[0].get("evidence_id"))
        return AdmissionEvidence(AdmissionState(status), sid, amount_0g, chain, record.get("source_id"),
                                 record.get("mechanism"), record.get("evidence_class"),
                                 # USD bound is retained in capture; native-only bounds
                                 # must not be misrepresented using an invented price.
                                 scalar_headroom_usd=None if record.number("scalar_headroom_usd") is None else float(record.number("scalar_headroom_usd")),
                                 capture=record.to_dict(),
                                 diagnostics=tuple(diagnostics) + ('CAPTURE_VALID_UNDER_OPERATIONAL_POLICY',) +
                                 (("EXPLICIT_MODELLED_DEMO_MODE",) if record.get("evidence_class") == "MODELLED" else ()),
                                 validity=next(a for a in assessments if a['evidence_id'] == record.get('evidence_id')),
                                 validity_records=tuple(sorted(assessments, key=lambda a: a["evidence_id"])))
