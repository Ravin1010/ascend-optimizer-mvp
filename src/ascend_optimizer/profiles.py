"""Frozen Conservative / Balanced / Aggressive optimizer constraints.

These values come directly from the capstone MVP specification. They are
measurable portfolio constraints rather than a synthetic 0-100 risk score.

All rate-like limits are decimal fractions: 0.05 means 5%.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import isfinite


class ProfileName(str, Enum):
    """Supported user risk profiles."""

    CONSERVATIVE = "Conservative"
    BALANCED = "Balanced"
    AGGRESSIVE = "Aggressive"


@dataclass(frozen=True)
class RiskProfile:
    """Constraint limits used by the portfolio optimizer."""

    name: ProfileName
    max_strategy_concentration: float
    max_bridge_exposure: float
    max_entry_exit_slippage: float
    max_portfolio_lp_il_stress: float
    max_exit_time_days: float
    max_slashing_stress_loss: float

    def __post_init__(self) -> None:
        fraction_fields = (
            "max_strategy_concentration",
            "max_bridge_exposure",
            "max_entry_exit_slippage",
            "max_portfolio_lp_il_stress",
            "max_slashing_stress_loss",
        )

        for field_name in fraction_fields:
            value = float(getattr(self, field_name))
            if not isfinite(value) or value < 0 or value > 1:
                raise ValueError(
                    f"{field_name} must be a finite fraction between 0 and 1"
                )

        exit_days = float(self.max_exit_time_days)
        if not isfinite(exit_days) or exit_days <= 0:
            raise ValueError("max_exit_time_days must be finite and > 0")


PROFILES: dict[ProfileName, RiskProfile] = {
    ProfileName.CONSERVATIVE: RiskProfile(
        name=ProfileName.CONSERVATIVE,
        max_strategy_concentration=0.40,
        max_bridge_exposure=0.10,
        max_entry_exit_slippage=0.005,
        max_portfolio_lp_il_stress=0.02,
        max_exit_time_days=7.0,
        max_slashing_stress_loss=0.02,
    ),
    ProfileName.BALANCED: RiskProfile(
        name=ProfileName.BALANCED,
        max_strategy_concentration=0.60,
        max_bridge_exposure=0.25,
        max_entry_exit_slippage=0.01,
        max_portfolio_lp_il_stress=0.05,
        max_exit_time_days=30.0,
        max_slashing_stress_loss=0.05,
    ),
    ProfileName.AGGRESSIVE: RiskProfile(
        name=ProfileName.AGGRESSIVE,
        max_strategy_concentration=0.80,
        max_bridge_exposure=0.50,
        max_entry_exit_slippage=0.03,
        max_portfolio_lp_il_stress=0.10,
        max_exit_time_days=90.0,
        max_slashing_stress_loss=0.10,
    ),
}


def normalize_profile_name(value: ProfileName | str) -> ProfileName:
    """Resolve enum/value/name strings to a supported profile."""

    if isinstance(value, ProfileName):
        return value

    normalized = str(value).strip().lower()

    for profile_name in ProfileName:
        if normalized in {
            profile_name.value.lower(),
            profile_name.name.lower(),
        }:
            return profile_name

    allowed = ", ".join(profile.value for profile in ProfileName)
    raise ValueError(f"Unknown risk profile {value!r}; expected one of: {allowed}")


def get_profile(value: ProfileName | str) -> RiskProfile:
    """Return one frozen risk profile."""

    return PROFILES[normalize_profile_name(value)]


def list_profiles() -> tuple[RiskProfile, ...]:
    """Return profiles in UI order: Conservative, Balanced, Aggressive."""

    return tuple(PROFILES[name] for name in ProfileName)
