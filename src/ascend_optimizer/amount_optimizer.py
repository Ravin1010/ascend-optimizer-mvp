"""Deterministic amount-aware decision-sleeve search, separate from the LP benchmark.

Admission providers must supply explicit point/bound evidence; no TVL fallback.
No holdings acquisition, freshness enforcement or new stress model is performed.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from enum import Enum
from itertools import product
from math import isfinite
from typing import Callable

import pandas as pd

from .collectors.common import CollectionError
from .data_loader import MVP_STRATEGY_IDS
from .exposure_engine import build_strategy_exposure, latest_snapshot_rows
from .lp_execution import LP_ROUTE_CONFIG, LPExecutionQuote, MODELLED_LP_STRESS_20PCT, estimate_lp_execution_slippage
from .net_return_engine import ReturnCalculationError, calculate_from_snapshot
from .profiles import RiskProfile, get_profile
from .strategy_state import strategy_state

WEIGHT_TOLERANCE = 1e-10
PROFIT_TOLERANCE_USD = 1e-8
GRID_STEP = 0.1
COST_FIELDS = ("gas_cost_usd", "bridge_cost_usd", "deposit_cost_usd", "withdrawal_cost_usd")


class AdmissionState(str, Enum):
    SUPPORTED = "SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class AdmissionEvidence:
    status: AdmissionState
    strategy_id: str
    amount_0g: float
    chain_id: int
    source: str
    mechanism: str
    evidence_class: str
    scalar_headroom_usd: float | None = None


def unknown_admission(*, strategy: pd.Series, amount_0g: float, **kwargs) -> AdmissionEvidence:
    return AdmissionEvidence(AdmissionState.UNKNOWN, str(strategy.strategy_id), amount_0g,
                             int(strategy.execution_chain_id), "UNAVAILABLE", "No explicit admission evidence", "MISSING/UNRESOLVED")


AdmissionFn = Callable[..., AdmissionEvidence]
QuoteFn = Callable[..., LPExecutionQuote]


@dataclass(frozen=True)
class AmountCandidate:
    strategy_id: str
    weight: float
    amount_0g: float
    amount_usd: float
    net_profit_usd: float | None = None
    net_return_horizon: float | None = None
    net_apy: float | None = None
    fixed_execution_cost_usd: float | None = None
    technical_admission: str = "UNKNOWN"
    admission_evidence: AdmissionEvidence | None = None
    runtime_execution: str = "NOT_TESTED"
    eligible: bool = False
    rejection_reasons: tuple[str, ...] = ()
    quote_context: dict | None = None
    entry_slippage_rate: float | None = None
    exit_slippage_rate: float | None = None
    bridge_fraction: float | None = None
    lp_stress_loss_20pct: float | None = None
    slashing_stress_loss: float | None = None
    exit_time_days: float | None = None


def candidate_grid(profile: RiskProfile) -> tuple[float, ...]:
    cap = float(profile.max_strategy_concentration)
    # Include the exact cap even for an explicitly supplied non-decimal profile.
    return tuple(sorted({0.0, cap, *(k / 10 for k in range(1, 11) if k / 10 <= cap)}))


def _number(value) -> float | None:
    if value is None or pd.isna(value):
        return None
    value = float(value)
    return value if isfinite(value) else None


def evaluate_candidate(strategy: pd.Series, snapshot: pd.Series | None, *, weight: float,
                       decision_amount: float, price_usd: float, horizon_days: float,
                       profile: RiskProfile, admission_fn: AdmissionFn = unknown_admission,
                       lp_quote_fn: QuoteFn = estimate_lp_execution_slippage,
                       management_fee_rate: float = 0, performance_fee_rate: float = 0,
                       stage: str = "CANDIDATE") -> AmountCandidate:
    sid = str(strategy.strategy_id)
    state = strategy_state(strategy)
    if sid not in MVP_STRATEGY_IDS or not state.structural_candidate:
        raise ValueError("Non-members cannot receive independent amount candidates")
    if not isfinite(weight) or not 0 <= weight <= 1:
        raise ValueError("candidate weight must be finite in [0,1]")
    for name, value in (("decision_amount", decision_amount), ("price_usd", price_usd), ("horizon_days", horizon_days)):
        if not isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be finite and positive")
    c = AmountCandidate(sid, weight, decision_amount * weight, decision_amount * price_usd * weight)
    if weight == 0:
        return replace(c, net_profit_usd=0, net_return_horizon=0, fixed_execution_cost_usd=0,
                       technical_admission="NOT_REQUIRED", runtime_execution="NOT_REQUIRED", eligible=True,
                       bridge_fraction=0, lp_stress_loss_20pct=0, slashing_stress_loss=0)
    reasons = []
    if not state.allocation_admitted:
        return replace(c, rejection_reasons=state.admission_reasons)
    if weight > profile.max_strategy_concentration + WEIGHT_TOLERANCE:
        reasons.append("PROFILE_CONCENTRATION_LIMIT")
    try:
        evidence = admission_fn(strategy=strategy.copy(), snapshot=None if snapshot is None else snapshot.copy(),
                                amount_0g=c.amount_0g, amount_usd=c.amount_usd, stage=stage)
        if not isinstance(evidence, AdmissionEvidence) or not isinstance(evidence.status, AdmissionState):
            raise ValueError("typed admission evidence required")
        if (evidence.strategy_id != sid or evidence.amount_0g != c.amount_0g
                or evidence.chain_id != int(strategy.execution_chain_id)):
            raise ValueError("admission evidence strategy/amount/chain mismatch")
        if evidence.status == AdmissionState.SUPPORTED and (not evidence.source or not evidence.mechanism
                or evidence.evidence_class not in {"LIVE_OBSERVED", "LIVE_DERIVED", "MODELLED", "STATIC_CONFIG", "HISTORICAL"}):
            raise ValueError("supported admission requires explicit evidence basis")
        if evidence.scalar_headroom_usd is not None:
            headroom = _number(evidence.scalar_headroom_usd)
            if headroom is None or headroom < 0:
                raise ValueError("invalid technical headroom")
            if c.amount_usd > headroom:
                evidence = replace(evidence, status=AdmissionState.UNSUPPORTED)
        c = replace(c, technical_admission=evidence.status.value, admission_evidence=evidence)
        if evidence.status != AdmissionState.SUPPORTED:
            reasons.append("TECHNICAL_ADMISSION_" + evidence.status.value)
    except (ValueError, CollectionError) as exc:
        reasons.append("ADMISSION_EVIDENCE_UNAVAILABLE: " + str(exc))
    if snapshot is None:
        return replace(c, rejection_reasons=tuple(reasons + ["MISSING_SNAPSHOT"]))
    snapshot = snapshot.copy(deep=True)
    # Always quote each supported positive LP point, even with prefilled rates.
    # Unknown admission points do not trigger unnecessary network requests.
    if sid in LP_ROUTE_CONFIG:
        if c.technical_admission != "SUPPORTED":
            return replace(c, rejection_reasons=tuple(reasons))
        try:
            quote = lp_quote_fn(strategy_id=sid, snapshot=snapshot.copy(), amount_0g=c.amount_0g, asset_price_usd=price_usd)
            if (not isfinite(quote.entry_amount_out_usdc) or quote.entry_amount_out_usdc <= 0
                    or not isfinite(quote.exit_amount_out_0g) or quote.exit_amount_out_0g <= 0
                    or not isinstance(quote.fee_tier, int) or quote.fee_tier <= 0):
                raise CollectionError("invalid quote output/fee context")
            if quote.strategy_id != sid:
                raise CollectionError("quote strategy mismatch")
            for rate in (quote.entry_slippage_rate, quote.exit_slippage_rate):
                if not isfinite(rate) or not 0 <= rate <= 1:
                    raise CollectionError("invalid quote loss fraction")
            snapshot["entry_slippage_rate"] = quote.entry_slippage_rate
            snapshot["exit_slippage_rate"] = quote.exit_slippage_rate
            if _number(snapshot.get("lp_stress_loss_20pct")) is None:
                snapshot["lp_stress_loss_20pct"] = MODELLED_LP_STRESS_20PCT
            c = replace(c, runtime_execution="TESTED_PROXY", quote_context={
                "amount_0g": c.amount_0g, "price_usd": price_usd, "quote": asdict(quote),
                "snapshot_notes": str(snapshot.get("notes", "")),
                "basis": "CURRENT_QUOTER_AND_MODELLED_EXIT_INVENTORY",
                "registered_configuration_alignment": "NOT_ESTABLISHED",
                "exit_inventory": "CURRENT_TARGET_PROXY_NOT_FUTURE_POSITION",
            })
        except (CollectionError, ValueError) as exc:
            return replace(c, runtime_execution="FAILED", rejection_reasons=tuple(reasons + ["RUNTIME_QUOTE_UNAVAILABLE: " + str(exc)]))
    else:
        c = replace(c, runtime_execution="SNAPSHOT_PROXY")
    exposure = build_strategy_exposure(strategy, snapshot)
    fields = ("entry_slippage_rate", "exit_slippage_rate", "exit_time_days", "bridge_fraction", "lp_stress_loss_20pct", "slashing_stress_loss")
    values = {field: _number(getattr(exposure, field)) for field in fields}
    for field, value in values.items():
        if value is None:
            reasons.append("MISSING_" + field)
        elif value < 0 or (field != "exit_time_days" and value > 1):
            reasons.append("INVALID_" + field)
    c = replace(c, **values)
    if all(values[f] is not None for f in ("entry_slippage_rate", "exit_slippage_rate")):
        if max(values["entry_slippage_rate"], values["exit_slippage_rate"]) > profile.max_entry_exit_slippage:
            reasons.append("PROFILE_SLIPPAGE_LIMIT")
    if values["exit_time_days"] is not None and values["exit_time_days"] > profile.max_exit_time_days:
        reasons.append("PROFILE_EXIT_TIME_LIMIT")
    if str(snapshot.get("yield_fee_status")) not in {"NET_OF_PROTOCOL_FEES", "GROSS_BEFORE_FEES"}:
        reasons.append("FEE_BASIS_UNRESOLVED")
    # Missing monetary costs stay missing. Known USD costs retain the existing
    # engine's fixed-per-positive-lifecycle convention, not measured provenance.
    for field in COST_FIELDS + ("protocol_fee_rate", "incentive_apy"):
        if _number(snapshot.get(field)) is None:
            reasons.append("MISSING_COST_OR_RETURN_COMPONENT: " + field)
    if not any(reason.startswith(("MISSING_COST_OR_RETURN_COMPONENT", "MISSING_entry_slippage_rate", "MISSING_exit_slippage_rate", "INVALID_entry_slippage_rate", "INVALID_exit_slippage_rate")) for reason in reasons):
        try:
            result = calculate_from_snapshot(snapshot, amount=c.amount_0g, asset_price_usd=price_usd,
                                             horizon_days=horizon_days, management_fee_rate=management_fee_rate,
                                             performance_fee_rate=performance_fee_rate)
            c = replace(c, net_profit_usd=result.net_profit_usd, net_return_horizon=result.net_return_horizon,
                        net_apy=result.net_apy, fixed_execution_cost_usd=result.fixed_execution_cost_usd)
        except ReturnCalculationError as exc:
            reasons.append("RETURN_UNAVAILABLE: " + str(exc))
    return replace(c, eligible=not reasons, rejection_reasons=tuple(reasons))


@dataclass(frozen=True)
class AmountAwareRun:
    decision_amount: float
    price_usd: float
    horizon_days: float
    profile: str
    grid: tuple[float, ...]
    candidates: tuple[AmountCandidate, ...]
    selected: tuple[AmountCandidate, ...]
    revalidation: str
    revalidation_errors: tuple[str, ...]
    combinations_tested: int
    reported_non_members: tuple[str, ...]
    management_fee_rate: float = 0
    performance_fee_rate: float = 0

    def to_dict(self) -> dict:
        valid = self.revalidation != "FAILED"
        deployed = sum(c.weight for c in self.selected)
        profit = sum(c.net_profit_usd for c in self.selected)
        selected_ids = {c.strategy_id for c in self.selected}
        ids = list(dict.fromkeys(c.strategy_id for c in self.candidates))
        return {
            "method": "AMOUNT_GRID_ENUMERATION_V1", "scope": "DECISION_SLEEVE",
            "whole_portfolio_compliance": "NOT_ASSESSED", "profile": self.profile,
            "decision_amount_0g": self.decision_amount, "decision_value_usd": self.decision_amount * self.price_usd,
            "price_usd": self.price_usd, "horizon_days": self.horizon_days,
            "management_fee_rate": self.management_fee_rate, "performance_fee_rate": self.performance_fee_rate,
            "grid": list(self.grid), "weight_tolerance": WEIGHT_TOLERANCE,
            "profit_tolerance_usd": PROFIT_TOLERANCE_USD, "combinations_tested": self.combinations_tested,
            "selected_amount_revalidation": self.revalidation, "revalidation_errors": list(self.revalidation_errors),
            "outcome": "SELECTED_REVALIDATION_FAILED" if not valid else "RECOMMENDATION_GENERATED" if self.selected else "NO_POSITIVE_ALLOCATION",
            "execution_readiness": "NOT_ESTABLISHED", "live_capstone_proof": "NOT_ESTABLISHED",
            "risk_basis": "LEGACY_SLEEVE_COEFFICIENTS", "cost_basis": "EXISTING_FIXED_USD_LIFECYCLE_CONVENTION_PROVENANCE_UNRESOLVED",
            "candidates": [asdict(c) for c in self.candidates],
            "proposed_selected": [asdict(c) for c in self.selected],
            "strategy_results": {sid: "REVALIDATION_FAILED" if sid in selected_ids and not valid else
                                 "ALLOCATED_POSITIVE" if sid in selected_ids else
                                 "GATED" if any("allocation_gate=CLOSED" in c.rejection_reasons for c in self.candidates if c.strategy_id == sid) else
                                 "ELIGIBLE_ZERO" if any(c.eligible and c.weight > 0 for c in self.candidates if c.strategy_id == sid) else "EXCLUDED"
                                 for sid in ids},
            "reported_non_members": list(self.reported_non_members),
            "recommendation": None if not valid else {
                "allocations": {c.strategy_id: {"weight": c.weight, "amount_0g": c.amount_0g, "amount_usd": c.amount_usd} for c in self.selected},
                "idle_weight": max(0, 1 - deployed), "idle_amount_0g": self.decision_amount * max(0, 1 - deployed),
                "expected_net_profit_usd": profit, "expected_net_return_horizon": profit / (self.decision_amount * self.price_usd),
                "legacy_stress": {f: sum(c.weight * getattr(c, f) for c in self.selected) for f in
                                  ("bridge_fraction", "lp_stress_loss_20pct", "slashing_stress_loss")},
            },
        }


def run_amount_optimizer(strategies: pd.DataFrame, snapshots: pd.DataFrame, *, decision_amount: float,
                         price_usd: float, horizon_days: float, profile: RiskProfile | str,
                         admission_fn: AdmissionFn = unknown_admission,
                         lp_quote_fn: QuoteFn = estimate_lp_execution_slippage,
                         management_fee_rate: float = 0, performance_fee_rate: float = 0) -> AmountAwareRun:
    profile = profile if isinstance(profile, RiskProfile) else get_profile(profile)
    for name, value in (("decision_amount", decision_amount), ("price_usd", price_usd), ("horizon_days", horizon_days)):
        if not isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be finite and positive")
    if strategies.strategy_id.duplicated().any():
        raise ValueError("duplicate strategy IDs")
    members = strategies[strategies.apply(lambda row: strategy_state(row).structural_candidate, axis=1)]
    if set(members.strategy_id) != MVP_STRATEGY_IDS:
        raise ValueError("exactly the five frozen structural members are required")
    latest = latest_snapshot_rows(snapshots)
    by_id = {str(row.strategy_id): row for _, row in latest.iterrows()}
    grid = candidate_grid(profile)
    def evaluate(meta, w, stage):
        return evaluate_candidate(meta, by_id.get(str(meta.strategy_id)), weight=w, decision_amount=decision_amount,
                                  price_usd=price_usd, horizon_days=horizon_days, profile=profile,
                                  admission_fn=admission_fn, lp_quote_fn=lp_quote_fn, stage=stage,
                                  management_fee_rate=management_fee_rate, performance_fee_rate=performance_fee_rate)
    candidates = tuple(evaluate(meta, w, "CANDIDATE") for _, meta in members.iterrows() for w in grid)
    options = [[c for c in candidates if c.strategy_id == sid and c.eligible] for sid in members.strategy_id]
    best = tuple(group[0] for group in options)  # all zero
    best_profit = best_deployed = 0.0
    tested = 0
    for combo in product(*options):
        tested += 1
        deployed = sum(c.weight for c in combo)
        if deployed > 1 + WEIGHT_TOLERANCE:
            continue
        if any(sum(c.weight * getattr(c, field) for c in combo) > limit + WEIGHT_TOLERANCE for field, limit in (
            ("bridge_fraction", profile.max_bridge_exposure), ("lp_stress_loss_20pct", profile.max_portfolio_lp_il_stress),
            ("slashing_stress_loss", profile.max_slashing_stress_loss))):
            continue
        profit = sum(c.net_profit_usd for c in combo)
        better = profit > best_profit + PROFIT_TOLERANCE_USD
        if abs(profit - best_profit) <= PROFIT_TOLERANCE_USD:
            better = deployed < best_deployed - WEIGHT_TOLERANCE or (
                abs(deployed - best_deployed) <= WEIGHT_TOLERANCE and tuple(-c.weight for c in combo) < tuple(-c.weight for c in best))
        if better:
            best, best_profit, best_deployed = combo, profit, deployed
    selected = tuple(c for c in best if c.weight > 0)
    errors = []
    # Repeat the exact selected points, no substitution/scaling/retry. Any change
    # invalidates the selection even when the new quote still passes a limit.
    for c in selected:
        meta = strategies[strategies.strategy_id == c.strategy_id].iloc[0]
        refreshed = evaluate(meta, c.weight, "REVALIDATION")
        if not refreshed.eligible or refreshed != c:
            errors.append(c.strategy_id + ": selected candidate evidence/economics changed or failed")
    for c in selected:
        final_state = strategy_state(strategies[strategies.strategy_id == c.strategy_id].iloc[0])
        if not final_state.allocation_admitted:
            errors.append(c.strategy_id + ": metadata admission changed during revalidation")
    return AmountAwareRun(decision_amount, price_usd, horizon_days, profile.name.value, grid, candidates, selected,
                          "FAILED" if errors else "PASSED" if selected else "NOT_REQUIRED", tuple(errors), tested,
                          tuple(strategies.loc[~strategies.strategy_id.isin(MVP_STRATEGY_IDS), "strategy_id"]),
                          management_fee_rate, performance_fee_rate)
