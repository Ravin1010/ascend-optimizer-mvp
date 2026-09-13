"""Collector for Gimo st0G liquid staking."""

from __future__ import annotations

from dataclasses import dataclass
import re

from bs4 import BeautifulSoup

from .common import CollectionError, fetch_html, utc_now_iso


STRATEGY_ID = "GIMO_STAKE_0G"
APP_URL = "https://app.gimofinance.xyz/"
DOCS_URL = "https://docs.gimofinance.xyz/docs/token/st0g/"

DOCUMENTED_REWARD_COMMISSION = 0.10
DOCUMENTED_EPOCH_DAYS = 22.0


@dataclass(frozen=True)
class GimoAppObservation:
    """Values exposed by the public Gimo staking application."""

    displayed_apr: float
    st0g_token_contract: str
    stake_contract: str


def _page_text(html_or_text: str) -> str:
    return BeautifulSoup(html_or_text, "html.parser").get_text(" ", strip=True)


def _required_match(pattern: str, text: str, field: str) -> str:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        raise CollectionError(f"Could not parse {field} from Gimo app")
    return match.group(1)


def parse_gimo_app(html_or_text: str) -> GimoAppObservation:
    """Parse displayed APR and verified contract addresses from the Gimo app."""

    text = _page_text(html_or_text)

    apr = float(
        _required_match(
            r"APR\s+([0-9]+(?:\.[0-9]+)?)%",
            text,
            "APR",
        )
    ) / 100.0
    token_contract = _required_match(
        r"st0G\s+Token\s+Contract\s+Address\s+(0x[a-fA-F0-9]{40})",
        text,
        "st0G token contract",
    )
    stake_contract = _required_match(
        r"st0G\s+Stake\s+Contract\s+Address\s+(0x[a-fA-F0-9]{40})",
        text,
        "stake contract",
    )

    return GimoAppObservation(
        displayed_apr=apr,
        st0g_token_contract=token_contract,
        stake_contract=stake_contract,
    )


def build_gimo_snapshot(
    observation: GimoAppObservation,
    *,
    timestamp: str | None = None,
) -> dict[str, object]:
    """Build a Gimo snapshot while preserving unresolved fee semantics."""

    return {
        "timestamp": timestamp or utc_now_iso(),
        "strategy_id": STRATEGY_ID,
        "gross_apr": observation.displayed_apr,
        "gross_apy": None,
        "incentive_apy": 0.0,
        # Gimo documents a 10% reward commission, but its public docs/app do not
        # establish whether the displayed APR is before or after that commission.
        # UNKNOWN intentionally blocks Net Return calculation when fee_rate > 0.
        "yield_fee_status": "UNKNOWN",
        "tvl_usd": None,
        "liquidity_usd": None,
        "volume_24h_usd": None,
        "protocol_fee_rate": DOCUMENTED_REWARD_COMMISSION,
        "gas_cost_usd": None,
        "bridge_cost_usd": 0.0,
        "deposit_cost_usd": None,
        "withdrawal_cost_usd": None,
        "entry_slippage_rate": 0.0,
        "exit_slippage_rate": 0.0,
        # Docs say withdrawals are aligned with the 22-day epoch cycle. We use
        # 22 days as a conservative maximum for the MVP and disclose it here.
        "exit_time_days": DOCUMENTED_EPOCH_DAYS,
        "slashing_stress_loss": None,
        "bridge_fraction": 0.0,
        "lp_stress_loss_20pct": None,
        "data_status": "LIVE_INCOMPLETE",
        "source": "GIMO_APP_AND_DOCS",
        "notes": (
            "Live displayed APR from Gimo app; 10% reward commission and "
            "22-day epoch alignment from Gimo docs; displayed APR fee basis "
            "unresolved; rewards stop accruing when unstaking begins; "
            f"st0G={observation.st0g_token_contract}; "
            f"stake={observation.stake_contract}"
        ),
    }


def collect_gimo_snapshot() -> dict[str, object]:
    """Collect the current public Gimo app observation."""

    observation = parse_gimo_app(fetch_html(APP_URL))
    return build_gimo_snapshot(observation)
