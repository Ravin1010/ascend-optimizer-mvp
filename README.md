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
7. provenance registry plus initial live collectors for Native 0G staking and Gimo st0G.

## Data files

- `data/strategies.csv` — relatively static strategy metadata.
- `data/strategy_snapshots.csv` — real-data scaffold; unknown values remain blank.
- `data/demo_strategy_snapshots.csv` — explicitly synthetic/modelled values used only for tests and demonstrations.
- `data/source_registry.csv` — field-level source/provenance registry.
- `data/live_strategy_snapshots.csv` — generated locally by the collector CLI and intentionally not committed.

Collector runs append timestamped rows to `live_strategy_snapshots.csv`; existing observations are preserved.

## Live collection

~~~bash
pip install -r requirements.txt
python -m src.ascend_optimizer.collect
~~~

Or individually:

~~~bash
python -m src.ascend_optimizer.collect --collector native
python -m src.ascend_optimizer.collect --collector gimo
~~~

### Native 0G benchmark

The official Explorer exposes validator-level yield. The current collector uses a transparent four-validator sample and calculates a delegation-weighted APY. It is a **sampled benchmark**, not a claim to be the exact network-wide APY.

### Gimo on-chain yield

The Gimo frontend is client-rendered, so automated collection no longer scrapes its displayed APR.

Instead, the Gimo collector calls `getRate()` on the st0G token contract through the official 0G Mainnet RPC. It compares the current exchange rate with the rate approximately seven days earlier and annualizes the realized growth.

Gimo documentation states that the exchange rate reflects staking rewards after the protocol's 10% reward commission. Therefore these derived returns are marked `NET_OF_PROTOCOL_FEES`; the 10% commission is retained as provenance but is not deducted a second time.

This is a **realized trailing APY**, not a forward guarantee.

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
