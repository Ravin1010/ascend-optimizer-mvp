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

#### Native 0G exposure completion

The Native collector also resolves the optimizer's exposure inputs:

- `liquidity_usd` is a conservative capacity proxy equal to sampled active-validator delegation depth multiplied by the current W0G USD price;
- `exit_time_days` is derived from the official staking contract's `minWithdrawabilityDelay` block count and a recent observed 0G block-time window;
- `slashing_stress_loss` is currently a **modelled 5% severe-slash stress scenario**, based on the default double-sign slash fraction in 0G Foundation's Cosmos SDK fork. It is not represented as a verified current mainnet parameter.

Because the slashing stress is modelled while yield/delegation/withdrawal timing are collected live, a complete Native exposure snapshot is labelled `PARTIAL_MODELLED`.

### Gimo on-chain yield

The Gimo frontend is client-rendered, so automated collection does not depend on scraping its APR.

The collector reads the current st0G `getRate()` from the public 0G RPC and stores each observation locally. The public endpoint does not expose sufficiently old contract state for historical `eth_call` queries, so we do not assume archive-node access.

On the **first successful run**, Gimo is recorded with the current exchange rate but no APY. After at least 24 hours of local history, later runs annualize exchange-rate growth. Once approximately seven days of history exists, the sample closest to the seven-day target is used.

This produces a **realized trailing APY**, not a forward guarantee. Exchange-rate growth is treated as net of protocol reward fees, avoiding a second deduction of the documented commission.

#### Gimo exposure completion

The collector also derives current Gimo capacity from on-chain st0G
`totalSupply()` multiplied by `getRate()`, then converts the backed 0G
amount to USD using the same W0G spot-price source used elsewhere. This TVL is
used as a conservative optimizer capacity proxy.

Gimo does not add a separate protocol slashing mechanism, but st0G remains
exposed to the underlying 0G validator set. The MVP therefore reuses the same
**modelled 5% severe underlying-staking stress** used for Native 0G, clearly
labelled as modelled rather than a verified Gimo-specific mainnet parameter.

After this exposure completion, Gimo should have no remaining exposure-data
blockers; until the local exchange-rate history is at least 24 hours old, its
only expected readiness gap is yield.

### Jaine 0G/USDC.e LP

The Jaine collector discovers W0G/USDC.e pools directly from the Jaine V3 factory across standard fee tiers. It then uses GeckoTerminal pool data for current USD liquidity and 24-hour volume and derives a trailing swap-fee APR proxy.

Merkl campaign incentives are queried by pool address. Only `CAMPAIGN` APR breakdowns are added as incentive yield; Merkl protocol/native APR components are ignored to avoid double counting the separately-derived swap-fee APR. At optimizer runtime, Jaine's V1 quoter resolves entry/exit slippage for the actual user portfolio amount. LP +/-20% stress uses a transparent modelled concentrated-liquidity range `[0.8P0, 1.2P0]`; the worse +/-20% shock produces about 6.36% IL versus HODL.

### Oku / Uniswap V3 0G/USDC.e LP

The Oku route uses the underlying Uniswap V3 deployment on 0G. The collector discovers W0G/USDC.e pools directly from the verified Uniswap V3 factory, then uses GeckoTerminal for current USD liquidity and 24-hour volume and derives the same trailing swap-fee APR proxy used for Jaine.

Oku is treated as the interface rather than a separate AMM protocol. Merkl campaign incentives are queried by the selected pool address, while protocol/native APR components are excluded. At optimizer runtime, Oku's QuoterV2 resolves entry/exit slippage for the actual user portfolio amount. The same transparent `[0.8P0, 1.2P0]` concentrated-liquidity stress assumption is applied as for Jaine.

## Personalized live optimizer

After collecting live snapshots, run a personalized 0G allocation:

~~~bash
python -m src.ascend_optimizer.live_optimize \
  --amount 1000 \
  --horizon-days 90 \
  --profile Balanced
~~~

The command fetches the current 0G USD price automatically unless
`--price-usd` is supplied. It also resolves Jaine/Oku amount-dependent
slippage at runtime using the actual portfolio amount, then applies the frozen
risk-profile constraints.

Strategy-ranking status is profile-specific: `PROFILE_ELIGIBLE` means the
strategy passes the selected profile's limits, while `PROFILE_EXCLUDED`
includes the exact exclusion reason (for example,
`slippage_exceeds_profile_limit`).

For a reproducible run with a manual price:

~~~bash
python -m src.ascend_optimizer.live_optimize \
  --amount 1000 \
  --horizon-days 90 \
  --profile Balanced \
  --price-usd 1.00
~~~

The current live MVP accepts `0G` as input. `a0G` remains a distinct
Ascend-modelled asset and is not treated as an alias for 0G.

## Readiness, tests and demos

After collecting live data, inspect exactly which strategies are return-ready
and which exposure inputs still block optimizer eligibility:

~~~bash
python -m src.ascend_optimizer.readiness
~~~

Then run the test suite and existing demos:

~~~bash
pytest -q
python -m src.ascend_optimizer.main
python -m src.ascend_optimizer.demo
~~~

The demo dataset is not a claim about current protocol yields or risk.

## Linear MVP assumption

For the frozen linear program, each strategy's horizon Net Return coefficient is evaluated at the user's full portfolio notional. This is a deliberate first-order approximation. Fixed execution costs can later be refined with a nonlinear or mixed-integer formulation that recomputes costs at the actual allocated amount.

No secrets or private keys should be committed to the repository.
