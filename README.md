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
- `data/ascend_a0g_rate_history.csv` — generated local a0G exchange-rate history used to derive realized Ascend APY.

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
python -m src.ascend_optimizer.collect --collector ascend
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

## Live Ascend a0G integration

Ascend a0G is now treated as a live external protocol rather than a capstone-
defined synthetic receipt token.

The live 0G SourceCore/a0G vault is:

~~~text
0x4B3c2f55fa67679b382c979A082Df1B32079B4cB
~~~

Its underlying asset is W0G
`0x1Cd0690fF9a693f5EF2dD976660a8dAFc81A109c`.

`AscendProtocolAdapter.sol` wraps native 0G to W0G, deposits W0G into the live
a0G SourceCore, and treats the actual a0G shares received as AscendVault
strategy shares. a0G appreciation is exchange-rate yield, so it must not also be
notified through `RewardAccounting`.

The live SourceCore is ERC-4626-style for deposits but uses an asynchronous
Mellow withdrawal queue rather than normal synchronous `redeem()`. The adapter
therefore calls `requestWithdrawal(shares)`, records the protocol epoch, and
settles the epoch through `withdrawalQueue.claim(epoch, receiver)`. Multiple
AscendVault users can share one underlying protocol epoch; assets from that
epoch are distributed pro rata across their adapter request IDs.

The underlying Mellow/OFT/restaking path is treated as **embedded backing of
a0G**, not as a second independent optimizer allocation. `ASCEND_RESTAKE`
therefore remains in the strategy registry only as an explanatory exposure row
and is marked `EXCLUDED_EMBEDDED`.

Live a0G execution exists. The collector now measures bridge exposure directly
from SourceCore accounting: source-side W0G in SourceCore and the withdrawal
queue is treated as local liquidity, while the remaining oracle-valued NAV is
target-side/OFT economic exposure. The raw W0G balance locked in the OFT adapter
is retained as a bridged-principal reconciliation check.

The default live collector does not depend on Ethereum RPC availability.
Ethereum target-vault composition probing is optional research diagnostics
enabled with `ASCEND_DEEP_ETHEREUM_PROBE=1`.

For optimizer risk inputs, the MVP uses a transparent conservative slashing
scenario: the same 5% severe-slash calibration used for Native 0G/Gimo is
applied to the entire measured bridged share of a0G NAV. This is explicitly a
modelled stress scenario, not an asserted live Symbiotic slashing parameter.
Ascend remains excluded until sufficient exchange-rate history exists for a
realized APY and the live-data technical gate is deliberately lifted. The old `ascend_model.py` functions are kept
only to reproduce pre-launch experiments; its CLI now refuses to append those
model rows to live data.

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

The current live MVP accepts `0G` as input. a0G remains a distinct external
yield-bearing asset and is not treated as an alias for native 0G.

By default, the LIVE optimizer excludes strategies whose execution status is
`MODELLED` or `PARTIAL_MODELLED`, so an experimental Ascend assumption cannot
silently enter a portfolio presented as live. To run an explicit scenario that
mixes live routes with Ascend-modelled routes:

~~~bash
python -m src.ascend_optimizer.live_optimize \
  --amount 1000 \
  --horizon-days 90 \
  --profile Balanced \
  --include-modelled
~~~

Modelled rows remain visible in strategy ranking but are labelled
`SCOPE_EXCLUDED (modelled_strategy_excluded_by_default)` unless that flag is
supplied.

## Solidity vault foundation

Section 5 implementation has started with a minimal, testable contract boundary:

- `IStrategyAdapter.sol` — common protocol adapter interface;
- `StrategyManager.sol` — owner-controlled approved-adapter registry plus hard
  deposit/allocation ceilings;
- `A0GToken.sol` — non-rebasing Ascend a0G reference token whose mint/burn
  authority is restricted to the Ascend staking adapter;
- focused Hardhat tests and a mock adapter.

The optimizer remains off-chain and has no on-chain execution role.

The user-facing `AscendVault` now implements:

- native 0G and approved ERC-20 idle deposits;
- user-authorized allocation through approved adapters;
- per-user strategy-share accounting;
- deadline and minimum-share protection;
- hard strategy deposit and user-allocation ceilings;
- synchronous strategy withdrawal back to idle balance;
- asynchronous request/claim withdrawal records with ownership and
  minimum-output protection;
- emergency pause for new deposits/allocations while withdrawals remain
  available.

The first protocol-specific adapter is now implemented as
`Native0GStakingAdapter.sol`. It follows the official 0G validator interface:
native delegation is credited to adapter-owned validator shares, undelegation
enters the validator withdrawal queue, and `processWithdrawQueue()` is used
before a matured request is settled back to `AscendVault`.

Because the official validator interface requires the withdrawal fee to be paid
when `undelegate()` is called, the adapter keeps an explicit prefunded fee
reserve. This reserve is accounted separately from user staking proceeds and
can only be recovered by the adapter owner.

The adapter is intentionally fixed to one validator address per deployment;
multi-validator routing remains an off-chain/registry deployment decision rather
than an autonomous on-chain optimizer action.

The reward-accounting layer is now implemented in
`RewardAccounting.sol` using the accumulative reward-per-share model described
in Section 5.5. `AscendVault` checkpoints user entitlement before strategy
shares increase or decrease, and users can claim separately-accounted rewards
without withdrawing principal. Reward claims remain available while new
deposits/allocations are paused.

Only separately claimable rewards should be notified to `RewardAccounting`.
Yield already embedded in strategy share value or receipt-token exchange-rate
appreciation must not be duplicated here.

`AscendStakingAdapter.sol` and `A0GToken.sol` are retained as the earlier
**reference/pre-launch Ascend design**. They model direct validator delegation
plus a locally-issued 1:1 a0G receipt and are not the live production Ascend
integration.

The executable live path is now `AscendProtocolAdapter.sol`, which integrates
the external a0G SourceCore described above. Deployment work should target the
live adapter, not the reference token/adapter pair.


The Gimo liquid-staking execution path is now implemented in
`GimoAdapter.sol`. The adapter stakes native 0G into Gimo, measures the actual
st0G received, and treats those st0G units as the vault's strategy shares.
Position value is derived from st0G's live `getRate()`, so Gimo staking yield is
embedded in share value and must not also be sent to `RewardAccounting`.

Gimo withdrawals follow the protocol's `unstake(st0GAmount)` then delayed
`withdraw()` lifecycle. Because the underlying withdrawal entry point is
parameterless and can aggregate matured requests for the caller, the MVP adapter
serializes protocol exits to one outstanding Gimo withdrawal per adapter
deployment. This preserves AscendVault's per-request accounting and avoids
cross-user claim ambiguity.


The concentrated-liquidity execution layer is now implemented through a shared
`V3LiquidityAdapter.sol` plus thin venue wrappers:
`JaineLPAdapter.sol` and `OkuV3Adapter.sol`.

The shared adapter uses one immutable W0G/USDC.e pool, fee tier and tick range
per deployment. Native 0G is wrapped to W0G, a bounded portion is swapped into
USDC.e, and liquidity is managed through the venue's V3 NFT position manager.
Jaine uses its legacy V1-style router ABI while Oku/Uniswap uses Router02.

Vault LP shares are synthetic NAV shares rather than raw V3 liquidity units.
NAV includes active concentrated liquidity, uncollected LP fees and residual
W0G/USDC.e dust. Deposits mint shares against pre-deposit NAV, while withdrawals
take only their pro-rata liquidity, fee and dust entitlement. LP fee growth is
therefore embedded in strategy-share value and is not separately duplicated in
`RewardAccounting`.

The Jaine wrapper pins the verified 0G factory, router, position manager, W0G
and USDC.e addresses. The Oku wrapper now also pins Oku's published 0G factory,
Router02, and NonfungiblePositionManager addresses. For both venues, the exact
W0G/USDC.e pool, fee tier, and tick range remain deployment-time choices and
must be refreshed from live pool data immediately before deployment.

The restaking execution boundary is now implemented with
`RestakingAdapter.sol` and `IRestakingConnector.sol`. The adapter is fixed to
one immutable connector and forwards only bounded deposit/withdraw/claim
operations; it does not expose arbitrary target calls.

This generic layer remains useful for future independently investable
restaking routes. It is **not** currently used to represent Ascend's production
a0G backing, because the live a0G SourceCore already embeds the Mellow/OFT/
restaking path beneath the vault share. A separate Symbiotic connector should
only be added if a distinct user-depositable route is verified later.

Install and run the Solidity tests with:

~~~bash
npm install
npm run contracts:compile
npm run contracts:test
~~~

## Section 6.4 evaluation harness

The proposal's evaluation plan can now be run reproducibly across all three
frozen risk profiles for the same user case:

~~~bash
python -m src.ascend_optimizer.evaluation \
  --amount 1000 \
  --horizon-days 90
~~~

To evaluate the explicit Ascend scenario as well:

~~~bash
python -m src.ascend_optimizer.evaluation \
  --amount 1000 \
  --horizon-days 90 \
  --include-modelled
~~~

An optional `--csv <path>` writes a report-friendly profile comparison table.
The harness independently verifies concentration, bridge, LP-stress, and
slashing-stress limits after each solve.

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
