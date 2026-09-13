# Ascend Optimizer MVP

Capstone implementation for the **Strategy, Yield Optimizer & Multi-Asset Vault for Ascend (0G Labs)**.

## Current milestone

The first executable optimizer pipeline is now implemented:

1. validated strategy metadata and snapshot datasets;
2. Net Return Engine;
3. measurable Exposure Engine;
4. frozen Conservative / Balanced / Aggressive profiles;
5. SciPy constrained portfolio optimizer;
6. end-to-end pipeline joining all engines.

## Project structure

~~~text
.
├── data/
│   ├── strategies.csv
│   ├── strategy_snapshots.csv
│   └── demo_strategy_snapshots.csv
├── notebooks/
├── src/
│   └── ascend_optimizer/
│       ├── __init__.py
│       ├── data_loader.py
│       ├── demo.py
│       ├── exposure_engine.py
│       ├── main.py
│       ├── net_return_engine.py
│       ├── optimizer.py
│       ├── pipeline.py
│       └── profiles.py
├── tests/
├── requirements.txt
└── README.md
~~~

## Frozen MVP strategy universe

- Native 0G staking
- Gimo st0G staking
- Jaine 0G/USDC LP
- Oku / Uniswap V3 0G/USDC LP
- Ascend a0G staking
- Ascend / Symbiotic restaking
- Morpho 0G lending — excluded until an exact usable market is verified

## Data rules

- strategies.csv stores relatively static route metadata.
- strategy_snapshots.csv is the real-data scaffold. Unknown live values stay blank rather than being fabricated.
- demo_strategy_snapshots.csv contains **explicitly synthetic/modelled values only** so the complete optimizer can be demonstrated before live collection is finished.
- yield_fee_status uses GROSS_BEFORE_FEES, NET_OF_PROTOCOL_FEES, or UNKNOWN.
- Points are tracked separately and are **not** included in Base Net APY.
- Ascend-specific values without a verified live source remain explicitly labelled MODELLED or PARTIAL/MODELLED.

## Linear MVP assumption

For the frozen linear program, each strategy's horizon Net Return coefficient is evaluated at the user's full portfolio notional. This is a deliberate first-order approximation. Fixed execution costs can later be refined with a nonlinear or mixed-integer formulation that recomputes costs at the actual allocated amount.

## Codespaces

Install dependencies and run the full test suite:

~~~bash
pip install -r requirements.txt
pytest -q
~~~

Validate the real-data scaffold:

~~~bash
python -m src.ascend_optimizer.main
~~~

Run the illustrative 1,000 0G / 90-day end-to-end demo:

~~~bash
python -m src.ascend_optimizer.demo
~~~

The demo is not a claim about current protocol yields or risk. It exists only to verify that routing changes across the three frozen risk profiles.

No secrets or private keys should be committed to the repository.
