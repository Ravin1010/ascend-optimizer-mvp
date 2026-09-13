# Ascend Optimizer MVP

Capstone implementation for the **Strategy, Yield Optimizer & Multi-Asset Vault for Ascend (0G Labs)**.

## Current milestone

The first executable optimizer pipeline is implemented:

1. validated strategy metadata and snapshot datasets;
2. Net Return Engine;
3. measurable Exposure Engine;
4. frozen Conservative / Balanced / Aggressive profiles;
5. SciPy constrained portfolio optimizer;
6. end-to-end pipeline joining all engines;
7. provenance registry plus live collectors for Native 0G staking, Gimo st0G, Jaine 0G/USDC.e LP, and Oku / Uniswap V3 0G/USDC.e LP.

## Data files

- `data/strategies.csv` — relatively static strategy metadata.
- `data/strategy_snapshots.csv` — real-data scaffold; unknown values remain blank.
- `data/demo_strategy_snapshots.csv` — explicitly synthetic/modelled values used only for tests and demonstrations.
- `data/source_registry.csv` — field-level source/provenance registry.
- `data/live_strategy_snapshots.csv` — generated locally by the collector CLI.
- `data/gimo_rate_history.csv` — generated local st0G getRate history used to derive realized Gimo APY.

Generated live files are intentionally not committed.

## Live collection

~~~bash
pip install -r requirements.txt
python -m src.ascend_optimizer.collect
~~~

Or individually:

~~~bash
python -m src.ascend_optimizer.collect --collector native
python -m src.ascend_optimizer.collect --collector gimo
python -m src.ascend_optimizer.collect --collector jaine
python -m src.ascend_optimizer.collect --collector oku
~~~

### Native 0G benchmark

The official Explorer exposes validator-level yield. The current collector uses a transparent four-validator sample and calculates a delegation-weighted APY. It is a **sampled benchmark**, not a claim to be the exact network-wide APY.

### Gimo on-chain yield

The Gimo frontend is client-rendered, so automated collection does not depend on scraping its APR.

The collector reads the current st0G `getRate()` from the public 0G RPC and stores each observation locally. The public endpoint does not expose sufficiently old contract state for historical `eth_call` queries, so we do not assume archive-node access.

On the **first successful run**, Gimo is recorded with the current exchange rate but no APY. After at least 24 hours of local history, later runs annualize exchange-rate growth. Once approximately seven days of history exists, the sample closest to the seven-day target is used.

This produces a **realized trailing APY**, not a forward guarantee. Exchange-rate growth is treated as net of protocol reward fees, avoiding a second deduction of the documented commission.

### Jaine 0G/USDC.e LP

The Jaine collector discovers W0G/USDC.e pools directly from the Jaine V3 factory across standard fee tiers. It then uses GeckoTerminal pool data for current USD liquidity and 24-hour volume and derives a trailing swap-fee APR proxy.

Merkl incentive APY, amount-dependent slippage, and concentrated-liquidity +/-20% stress are intentionally left unresolved. The route therefore remains `LIVE_INCOMPLETE` until those inputs are implemented.

### Oku / Uniswap V3 0G/USDC.e LP

The Oku route uses the underlying Uniswap V3 deployment on 0G. The collector discovers W0G/USDC.e pools directly from the verified Uniswap V3 factory, then uses GeckoTerminal for current USD liquidity and 24-hour volume and derives the same trailing swap-fee APR proxy used for Jaine.

Oku is treated as the interface rather than a separate AMM protocol. Incentive APY, amount-dependent slippage, and concentrated-liquidity +/-20% stress remain unresolved, so the strategy stays `LIVE_INCOMPLETE`.

## Tests and demos

~~~bash
pytest -q
python -m src.ascend_optimizer.main
python -m src.ascend_optimizer.demo
~~~

The demo dataset is not a claim about current protocol yields or risk.

## Linear MVP assumption

For the frozen linear program, each strategy's horizon Net Return coefficient is evaluated at the user's full portfolio notional. This is a deliberate first-order approximation. Fixed execution costs can later be refined with a nonlinear or mixed-integer formulation that recomputes costs at the actual allocated amount.

No secrets or private keys should be committed to the repository.
