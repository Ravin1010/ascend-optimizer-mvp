# Ascend Optimizer MVP

Capstone implementation for the **Strategy, Yield Optimizer & Multi-Asset Vault for Ascend (0G Labs)**.

## Current milestone

Milestone 1 implementation begins with:

1. a reproducible Python project structure;
2. a static `strategies.csv` dataset;
3. a time-series `strategy_snapshots.csv` dataset;
4. explicit separation between LIVE, MODELLED, PARTIAL/MODELLED, and PENDING strategy data.

The next implementation stage will add the Net Return Engine, Exposure Engine, and constrained portfolio optimizer.

## Project structure

```text
.
├── data/
│   ├── strategies.csv
│   └── strategy_snapshots.csv
├── notebooks/
├── src/
│   └── ascend_optimizer/
│       ├── __init__.py
│       ├── data_loader.py
│       ├── exposure_engine.py
│       ├── main.py
│       ├── net_return_engine.py
│       ├── optimizer.py
│       └── profiles.py
├── tests/
├── requirements.txt
└── README.md
```

## Frozen MVP strategy universe

- Native 0G staking
- Gimo st0G staking
- Jaine 0G/USDC LP
- Oku / Uniswap V3 0G/USDC LP
- Ascend a0G staking
- Ascend / Symbiotic restaking
- Morpho 0G lending — excluded until an exact usable market is verified

## Data rules

- `strategies.csv` stores relatively static route metadata.
- `strategy_snapshots.csv` stores time-varying yield, liquidity, cost, slippage, exit-time, and risk observations.
- Unknown live values are intentionally left blank rather than fabricated.
- `yield_fee_status` uses:
  - `GROSS_BEFORE_FEES`
  - `NET_OF_PROTOCOL_FEES`
  - `UNKNOWN`
- Points are tracked separately and are **not** included in Base Net APY.
- Ascend-specific values without a verified live source must remain explicitly marked `MODELLED` or `PARTIAL_MODELLED`.

## Codespaces setup

In the Codespaces terminal:

```bash
python --version
pip install -r requirements.txt
python -m pytest
```

No secrets or private keys should be committed to the repository.
