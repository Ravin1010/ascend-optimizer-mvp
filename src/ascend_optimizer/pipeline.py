"""End-to-end integration of data, return, exposure, and optimizer engines.

The linear MVP treats each strategy's NetReturn_i,H as a coefficient evaluated
at the user's full portfolio notional V. This keeps the frozen optimization
problem linear. Fixed execution costs therefore remain a first-order MVP
approximation; a later nonlinear or mixed-integer model can recompute them per
allocated strategy amount.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .exposure_engine import build_exposure_table, latest_snapshot_rows
from .net_return_engine import (
    ReturnCalculationError,
    calculate_from_snapshot,
)
from .optimizer import PortfolioResult, optimize_portfolio
from .profiles import ProfileName, RiskProfile


@dataclass(frozen=True)
class PipelineRun:
    """Inputs transformed into optimizer candidates plus solved portfolio."""

    candidates: pd.DataFrame
    result: PortfolioResult


def build_optimizer_candidates(
    strategies: pd.DataFrame,
    snapshots: pd.DataFrame,
    *,
    amount: float,
    asset_price_usd: float,
    horizon_days: float,
    management_fee_rate: float = 0.0,
    performance_fee_rate: float = 0.0,
) -> pd.DataFrame:
    """Join latest snapshot returns with measurable strategy exposures."""

    exposure_table = build_exposure_table(strategies, snapshots)
    latest = latest_snapshot_rows(snapshots)

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
    )

    portfolio_value_usd = float(amount) * float(asset_price_usd)

    result = optimize_portfolio(
        candidates,
        portfolio_value_usd=portfolio_value_usd,
        profile=profile,
    )

    return PipelineRun(candidates=candidates, result=result)
