"""End-to-end integration of data, return, exposure, and optimizer engines.

The linear MVP treats each strategy's NetReturn_i,H as a coefficient evaluated
at the user's full portfolio notional V. This keeps the frozen optimization
problem linear. Fixed execution costs therefore remain a first-order MVP
approximation; a later nonlinear or mixed-integer model can recompute them per
allocated strategy amount.

LP entry/exit slippage is amount-dependent. For supported live LP routes, the
pipeline resolves those exposures at runtime from the actual user portfolio
amount rather than freezing a generic slippage number into collected snapshots.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pandas as pd

from .collectors.common import CollectionError
from .exposure_engine import build_exposure_table, latest_snapshot_rows
from .lp_execution import (
    LPExecutionQuote,
    LP_ROUTE_CONFIG,
    MODELLED_LP_STRESS_20PCT,
    estimate_lp_execution_slippage,
)
from .net_return_engine import (
    ReturnCalculationError,
    calculate_from_snapshot,
)
from .optimizer import PortfolioResult, optimize_portfolio
from .profiles import ProfileName, RiskProfile


LPQuoteFn = Callable[..., LPExecutionQuote]


@dataclass(frozen=True)
class PipelineRun:
    """Inputs transformed into optimizer candidates plus solved portfolio."""

    candidates: pd.DataFrame
    result: PortfolioResult


def _has_value(value: Any) -> bool:
    return value is not None and not pd.isna(value)


def _return_data_available(snapshot: pd.Series) -> bool:
    return (
        _has_value(snapshot.get("gross_apy"))
        or _has_value(snapshot.get("gross_apr"))
    )


def resolve_runtime_lp_exposures(
    snapshots: pd.DataFrame,
    *,
    amount: float,
    asset_price_usd: float,
    lp_quote_fn: LPQuoteFn = estimate_lp_execution_slippage,
) -> tuple[pd.DataFrame, dict[str, str]]:
    """Resolve amount-dependent LP slippage on each strategy's latest snapshot.

    Only supported LP routes with usable return data are quoted. Existing
    measured/modelled exposure values are preserved. The +/-20% concentrated-LP
    stress is the transparent MVP range stress from the lp_execution module.

    Quote failures are surfaced to the candidate table instead of making up
    fallback slippage.
    """

    latest = latest_snapshot_rows(snapshots).copy()
    errors: dict[str, str] = {}

    for index, snapshot in latest.iterrows():
        strategy_id = str(snapshot["strategy_id"])

        if strategy_id not in LP_ROUTE_CONFIG:
            continue

        if not _return_data_available(snapshot):
            continue

        missing_slippage = (
            not _has_value(snapshot.get("entry_slippage_rate"))
            or not _has_value(snapshot.get("exit_slippage_rate"))
        )

        if missing_slippage:
            try:
                quote = lp_quote_fn(
                    strategy_id=strategy_id,
                    snapshot=snapshot,
                    amount_0g=amount,
                    asset_price_usd=asset_price_usd,
                )
            except CollectionError as exc:
                errors[strategy_id] = str(exc)
            else:
                latest.at[index, "entry_slippage_rate"] = (
                    quote.entry_slippage_rate
                )
                latest.at[index, "exit_slippage_rate"] = (
                    quote.exit_slippage_rate
                )

        if not _has_value(snapshot.get("lp_stress_loss_20pct")):
            latest.at[index, "lp_stress_loss_20pct"] = (
                MODELLED_LP_STRESS_20PCT
            )

        complete = all(
            _has_value(latest.at[index, field])
            for field in (
                "entry_slippage_rate",
                "exit_slippage_rate",
                "lp_stress_loss_20pct",
            )
        )
        if complete:
            latest.at[index, "data_status"] = "PARTIAL_MODELLED"

    return latest, errors


def build_optimizer_candidates(
    strategies: pd.DataFrame,
    snapshots: pd.DataFrame,
    *,
    amount: float,
    asset_price_usd: float,
    horizon_days: float,
    management_fee_rate: float = 0.0,
    performance_fee_rate: float = 0.0,
    lp_quote_fn: LPQuoteFn = estimate_lp_execution_slippage,
) -> pd.DataFrame:
    """Join latest returns with measurable and runtime-resolved exposures."""

    latest, runtime_errors = resolve_runtime_lp_exposures(
        snapshots,
        amount=amount,
        asset_price_usd=asset_price_usd,
        lp_quote_fn=lp_quote_fn,
    )

    exposure_table = build_exposure_table(strategies, latest)

    snapshot_by_id = {
        str(row["strategy_id"]): row
        for _, row in latest.iterrows()
    }

    return_rows: list[dict[str, object]] = []

    for strategy_id in strategies["strategy_id"].astype(str):
        snapshot = snapshot_by_id.get(strategy_id)

        row: dict[str, object] = {
            "strategy_id": strategy_id,
            "net_return_horizon": pd.NA,
            "net_apy": pd.NA,
            "net_profit_usd": pd.NA,
            "gross_apy_used": pd.NA,
            "return_error": "",
            "runtime_exposure_error": runtime_errors.get(
                strategy_id,
                "",
            ),
        }

        if snapshot is None:
            row["return_error"] = "missing_snapshot"
            return_rows.append(row)
            continue

        try:
            result = calculate_from_snapshot(
                snapshot,
                amount=amount,
                asset_price_usd=asset_price_usd,
                horizon_days=horizon_days,
                management_fee_rate=management_fee_rate,
                performance_fee_rate=performance_fee_rate,
            )
        except ReturnCalculationError as exc:
            row["return_error"] = str(exc)
        else:
            row.update(
                {
                    "net_return_horizon": result.net_return_horizon,
                    "net_apy": result.net_apy,
                    "net_profit_usd": result.net_profit_usd,
                    "gross_apy_used": result.total_gross_apy,
                }
            )

        return_rows.append(row)

    returns = pd.DataFrame(return_rows)

    return exposure_table.merge(
        returns,
        on="strategy_id",
        how="left",
        validate="one_to_one",
    )


def run_optimizer_pipeline(
    strategies: pd.DataFrame,
    snapshots: pd.DataFrame,
    *,
    amount: float,
    asset_price_usd: float,
    horizon_days: float,
    profile: RiskProfile | ProfileName | str,
    management_fee_rate: float = 0.0,
    performance_fee_rate: float = 0.0,
    lp_quote_fn: LPQuoteFn = estimate_lp_execution_slippage,
) -> PipelineRun:
    """Build candidates and solve one personalized portfolio."""

    candidates = build_optimizer_candidates(
        strategies,
        snapshots,
        amount=amount,
        asset_price_usd=asset_price_usd,
        horizon_days=horizon_days,
        management_fee_rate=management_fee_rate,
        performance_fee_rate=performance_fee_rate,
        lp_quote_fn=lp_quote_fn,
    )

    portfolio_value_usd = float(amount) * float(asset_price_usd)

    result = optimize_portfolio(
        candidates,
        portfolio_value_usd=portfolio_value_usd,
        profile=profile,
    )

    return PipelineRun(candidates=candidates, result=result)
