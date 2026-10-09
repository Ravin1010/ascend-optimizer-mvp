"""Repository-only technical admission. No RPC, TVL, quote or freshness fallback."""
from __future__ import annotations

from decimal import Decimal, localcontext
from pathlib import Path
from typing import Mapping

from .admission_records import DEFAULT_ADMISSION_PATH, load_admission_records, timestamp_value
from .amount_optimizer import AdmissionEvidence, AdmissionState
from .data_loader import SchemaValidationError
from .strategy_state import strategy_state


class RepositoryAdmissionProvider:
    def __init__(self, path: str | Path = DEFAULT_ADMISSION_PATH, *, strategies=None,
                 config_identities: Mapping[str, str] | None = None, allow_modelled: bool = False):
        if not isinstance(allow_modelled, bool):
            raise ValueError("allow_modelled must be an explicit boolean demo/test opt-in")
        self.path = Path(path)
        self.strategies = strategies
        # Explicit caller context only; never infer config from notes/reference IDs.
        self.config_identities = dict(config_identities or {})
        self.allow_modelled = allow_modelled

    def __call__(self, *, strategy, amount_0g: float, amount_usd: float,
                 canonical_amount_0g: Decimal | None = None,
                 canonical_amount_usd: Decimal | None = None, **kwargs) -> AdmissionEvidence:
        sid, chain = str(strategy.strategy_id), int(strategy.execution_chain_id)
        def unknown(*diagnostics):
            return AdmissionEvidence(AdmissionState.UNKNOWN, sid, amount_0g, chain, "UNAVAILABLE",
                                     "No usable repository admission capture", "MISSING/UNRESOLVED",
                                     diagnostics=tuple(diagnostics))
        if not strategy_state(strategy).allocation_admitted:
            return unknown("METADATA_GATE_NOT_ADMITTED")
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
            if record.usability_gaps:
                diagnostics.extend(identity + ":" + gap for gap in record.usability_gaps)
                continue
            evidence_class = record.get("evidence_class")
            if evidence_class == "HISTORICAL" or (evidence_class == "MODELLED" and not self.allow_modelled):
                diagnostics.append(identity + ":EVIDENCE_CLASS_NOT_PRODUCTION_ADMISSION")
                continue
            if self.config_identities.get(sid) != record.get("config_identity"):
                diagnostics.append(identity + ":CONFIG_CONTEXT_MISSING_OR_MISMATCH")
                continue
            # USD-dependent bounds/points require the captured valuation context.
            usd_dependent = record.number("amount_usd") is not None or record.number("tested_amount_usd") is not None or record.number("scalar_headroom_usd") is not None
            if usd_dependent:
                price = record.number("valuation_price_usd")
                with localcontext() as context:
                    context.prec = max(28, len(amount.as_tuple().digits) + len(price.as_tuple().digits))
                    expected_usd = amount * price
                if usd != expected_usd:
                    diagnostics.append(identity + ":VALUATION_CONTEXT_MISMATCH")
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
            matched.append((record, status))
        if not matched:
            return unknown(*(diagnostics or ["NO_MATCHING_CAPTURE"]))
        # Never use specificity/recency to silently override a contradictory claim.
        if len({status for _, status in matched}) > 1:
            return unknown("CONFLICTING_CAPTURE_STATUSES: " + ",".join(sorted(r.get("evidence_id") for r, _ in matched)))
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
                                 diagnostics=("STRUCTURAL_CAPTURE_MATCH_NO_TTL_ASSESSMENT",) +
                                 (("EXPLICIT_MODELLED_DEMO_MODE",) if record.get("evidence_class") == "MODELLED" else ()))
