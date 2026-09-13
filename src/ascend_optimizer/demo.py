"""Run an illustrative end-to-end 1,000 0G / 90-day optimizer demo."""

from pathlib import Path

from .data_loader import load_snapshots, load_strategies
from .net_return_engine import annualize_horizon_return
from .pipeline import run_optimizer_pipeline
from .profiles import ProfileName


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    strategies = load_strategies(PROJECT_ROOT / "data" / "strategies.csv")
    snapshots = load_snapshots(
        strategies,
        PROJECT_ROOT / "data" / "demo_strategy_snapshots.csv",
    )

    amount = 1000.0
    asset_price_usd = 1.0
    horizon_days = 90.0

    print("Ascend Optimizer MVP - illustrative end-to-end demo")
    print("WARNING: demo_strategy_snapshots.csv is synthetic/modelled, not live data.")
    print("Input: 1,000 0G, assumed price $1.00, horizon 90 days")
    print()

    for profile in ProfileName:
        run = run_optimizer_pipeline(
            strategies,
            snapshots,
            amount=amount,
            asset_price_usd=asset_price_usd,
            horizon_days=horizon_days,
            profile=profile,
        )
        result = run.result

        print(profile.value)
        for strategy_id, weight in sorted(
            result.allocations.items(),
            key=lambda item: item[1],
            reverse=True,
        ):
            print(f"  {strategy_id:<24} {weight:>7.2%}")

        if result.idle_weight > 1e-10:
            print(f"  {'IDLE':<24} {result.idle_weight:>7.2%}")

        portfolio_net_apy = annualize_horizon_return(
            result.expected_net_return_horizon,
            horizon_days,
        )

        print(
            f"  Expected 90d Net Return: "
            f"{result.expected_net_return_horizon:.2%}"
        )
        print(f"  Annualized Net APY:      {portfolio_net_apy:.2%}")
        print(
            f"  Expected Net Profit:     $"
            f"{result.expected_net_profit_usd:.2f}"
        )
        print(
            f"  Bridge / LP / Slash:     "
            f"{result.portfolio_bridge_exposure:.2%} / "
            f"{result.portfolio_lp_il_stress:.2%} / "
            f"{result.portfolio_slashing_stress_loss:.2%}"
        )
        print()


if __name__ == "__main__":
    main()
