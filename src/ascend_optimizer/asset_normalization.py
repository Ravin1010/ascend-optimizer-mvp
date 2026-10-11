"""Semantic wrapping boundary only: no pricing, transactions or user-input expansion.

Mainnet address is a frozen external reference from data/strategies.csv and the
Iteration 18 architecture; it is not a capstone runtime/deployment identity.
"""
from dataclasses import dataclass
from enum import Enum

from .data_loader import load_strategies
from .strategy_state import strategy_state


class EconomicAssetFamily(str, Enum):
    ZERO_G = '0G'


class AssetRepresentation(str, Enum):
    NATIVE_0G = 'NATIVE_0G'
    W0G = 'W0G'


@dataclass(frozen=True)
class WrappedIdentity:
    chain_id: int
    address: str | None
    state: str
    evidence_source: str


VERSION = 'ASSET_NORMALIZATION_V1'
MAINNET_W0G = '0x1Cd0690fF9a693f5EF2dD976660a8dAFc81A109c'
DIRECT_W0G_INPUT = 'KIV_FUTURE'


def normalize_to_economic_asset(representation: AssetRepresentation | str) -> EconomicAssetFamily:
    """Wrapping representation equivalence, not a price-oracle assertion.

Only the two explicit execution representations are recognized. Receipt/share
assets (a0G, st0G), LP assets and unknown strings are not aliases for 0G.
"""
    AssetRepresentation(representation)  # reject unknown representations
    return EconomicAssetFamily.ZERO_G


def is_internal_execution_representation(representation: AssetRepresentation | str) -> bool:
    return AssetRepresentation(representation) is AssetRepresentation.W0G


def w0g_identity(chain_id: int, *, address: str | None = None) -> WrappedIdentity:
    """No RPC: validate supplied identity against this project's frozen reference.

A supplied address on an unresolved/unsupported chain fails closed, even if it
matches Mainnet. No other-chain reference is substituted into Galileo.
"""
    if type(chain_id) is not int or chain_id <= 0:
        raise ValueError('positive integer chain ID required')
    known = MAINNET_W0G if chain_id == 16661 else None
    if address is not None and (known is None or not isinstance(address, str)
                                or address.lower() != known.lower()):
        raise ValueError('W0G identity not established for this chain/address')
    state = 'EXTERNAL_PROTOCOL_REFERENCE' if known else 'UNRESOLVED_NOT_VERIFIED' if chain_id == 16602 else 'UNSUPPORTED'
    return WrappedIdentity(chain_id, known, state, 'data/strategies.csv; Iteration 18 architecture')


def strategy_execution_paths() -> dict[str, tuple[str, ...]]:
    """Read the five conceptual paths from authoritative metadata, not a new registry.

Paths are design descriptions only, not simulated transactions or runtime proof.
"""
    rows = load_strategies()
    return {row['strategy_id']: tuple(row['capital_path'].split('>'))
            for _, row in rows.iterrows() if strategy_state(row).structural_candidate}
