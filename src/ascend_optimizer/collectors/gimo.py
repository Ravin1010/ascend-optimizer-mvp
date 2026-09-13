"""Collector for Gimo st0G liquid staking.

Gimo's staking app is client-rendered for ordinary HTTP requests. The collector
therefore attempts the normal page first and then recognised crawler user agents,
which may receive prerendered application content. Parsing also inspects both
visible page text and raw HTML/script payloads.

The contract addresses below are verified static metadata. They are used as a
fallback when the client-rendered shell does not expose contract labels in the
initial HTML.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

from bs4 import BeautifulSoup

from .common import CollectionError, fetch_html, utc_now_iso


STRATEGY_ID = "GIMO_STAKE_0G"
APP_URL = "https://app.gimofinance.xyz/"
DOCS_URL = "https://docs.gimofinance.xyz/docs/token/st0g/"

VERIFIED_ST0G_TOKEN_CONTRACT = "0x7bBC63D01CA42491c3E084C941c3E86e55951404"
VERIFIED_STAKE_CONTRACT = "0xAc06d1Df23a4Fa00981aFAC0f33A5936Bd2135aF"

DOCUMENTED_REWARD_COMMISSION = 0.10
DOCUMENTED_EPOCH_DAYS = 22.0

BOT_USER_AGENTS = (
    (
        "googlebot",
        "Mozilla/5.0 (compatible; Googlebot/2.1; "
        "+http://www.google.com/bot.html)",
    ),
    (
        "bingbot",
        "Mozilla/5.0 (compatible; bingbot/2.0; "
        "+http://www.bing.com/bingbot.htm)",
    ),
)


@dataclass(frozen=True)
class GimoAppObservation:
    """Values exposed by the public Gimo staking application."""

    displayed_apr: float
    st0g_token_contract: str
    stake_contract: str
    retrieval_mode: str = "direct"


def _page_text(html_or_text: str) -> str:
    return BeautifulSoup(html_or_text, "html.parser").get_text(" ", strip=True)


def _match_first(
    patterns: tuple[str, ...],
    search_spaces: tuple[str, ...],
) -> str | None:
    for search_space in search_spaces:
        for pattern in patterns:
            match = re.search(
                pattern,
                search_space,
                flags=re.IGNORECASE | re.DOTALL,
            )
            if match:
                return match.group(1)
    return None


def parse_gimo_app(
    html_or_text: str,
    *,
    retrieval_mode: str = "direct",
) -> GimoAppObservation:
    """Parse displayed APR and contract addresses from Gimo app content."""

    visible_text = _page_text(html_or_text)
    search_spaces = (visible_text, html_or_text)

    apr_raw = _match_first(
        (
            r"APR\s+([0-9]+(?:\.[0-9]+)?)%",
            r"APR.{0,300}?([0-9]+(?:\.[0-9]+)?)%",
        ),
        search_spaces,
    )
    if apr_raw is None:
        raise CollectionError("Could not parse APR from Gimo app")

    token_contract = _match_first(
        (
            r"st0G\s+Token\s+Contract\s+Address\s+"
            r"(0x[a-fA-F0-9]{40})",
            r"st0G.{0,250}?Token.{0,250}?"
            r"(0x[a-fA-F0-9]{40})",
        ),
        search_spaces,
    ) or VERIFIED_ST0G_TOKEN_CONTRACT

    stake_contract = _match_first(
        (
            r"st0G\s+Stake\s+Contract\s+Address\s+"
            r"(0x[a-fA-F0-9]{40})",
            r"st0G.{0,250}?Stake.{0,250}?"
            r"(0x[a-fA-F0-9]{40})",
        ),
        search_spaces,
    ) or VERIFIED_STAKE_CONTRACT

    return GimoAppObservation(
        displayed_apr=float(apr_raw) / 100.0,
        st0g_token_contract=token_contract,
        stake_contract=stake_contract,
        retrieval_mode=retrieval_mode,
    )


def fetch_gimo_observation() -> GimoAppObservation:
    """Fetch Gimo, retrying with prerender-friendly crawler user agents."""

    errors: list[str] = []

    attempts = (("direct", None),) + tuple(
        (name, {"User-Agent": user_agent})
        for name, user_agent in BOT_USER_AGENTS
    )

    for mode, headers in attempts:
        try:
            html = fetch_html(APP_URL, headers=headers)
            return parse_gimo_app(html, retrieval_mode=mode)
        except CollectionError as exc:
            errors.append(f"{mode}:{exc}")

    raise CollectionError(
        "Could not parse Gimo APR after direct/googlebot/bingbot attempts: "
        + " | ".join(errors)
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
            "Live displayed APR from Gimo app; retrieval_mode="
            f"{observation.retrieval_mode}; 10% reward commission and "
            "22-day epoch alignment from Gimo docs; displayed APR fee basis "
            "unresolved; rewards stop accruing when unstaking begins; "
            f"st0G={observation.st0g_token_contract}; "
            f"stake={observation.stake_contract}"
        ),
    }


def collect_gimo_snapshot() -> dict[str, object]:
    """Collect the current public Gimo app observation."""

    return build_gimo_snapshot(fetch_gimo_observation())
