"""Tests for frozen optimizer risk profiles."""

import pytest

from src.ascend_optimizer.profiles import (
    PROFILES,
    ProfileName,
    RiskProfile,
    get_profile,
    list_profiles,
    normalize_profile_name,
)


def test_profile_values_match_frozen_capstone_table() -> None:
    conservative = get_profile("Conservative")
    balanced = get_profile("Balanced")
    aggressive = get_profile("Aggressive")

    assert conservative.max_strategy_concentration == pytest.approx(0.40)
    assert conservative.max_bridge_exposure == pytest.approx(0.10)
    assert conservative.max_entry_exit_slippage == pytest.approx(0.005)
    assert conservative.max_portfolio_lp_il_stress == pytest.approx(0.02)
    assert conservative.max_exit_time_days == pytest.approx(7)
    assert conservative.max_slashing_stress_loss == pytest.approx(0.02)

    assert balanced.max_strategy_concentration == pytest.approx(0.60)
    assert balanced.max_bridge_exposure == pytest.approx(0.25)
    assert balanced.max_entry_exit_slippage == pytest.approx(0.01)
    assert balanced.max_portfolio_lp_il_stress == pytest.approx(0.05)
    assert balanced.max_exit_time_days == pytest.approx(30)
    assert balanced.max_slashing_stress_loss == pytest.approx(0.05)

    assert aggressive.max_strategy_concentration == pytest.approx(0.80)
    assert aggressive.max_bridge_exposure == pytest.approx(0.50)
    assert aggressive.max_entry_exit_slippage == pytest.approx(0.03)
    assert aggressive.max_portfolio_lp_il_stress == pytest.approx(0.10)
    assert aggressive.max_exit_time_days == pytest.approx(90)
    assert aggressive.max_slashing_stress_loss == pytest.approx(0.10)


def test_profile_names_are_normalized_case_insensitively() -> None:
    assert normalize_profile_name("conservative") is ProfileName.CONSERVATIVE
    assert normalize_profile_name("BALANCED") is ProfileName.BALANCED
    assert normalize_profile_name(" Aggressive ") is ProfileName.AGGRESSIVE


def test_get_profile_accepts_enum() -> None:
    assert get_profile(ProfileName.BALANCED) is PROFILES[ProfileName.BALANCED]


def test_unknown_profile_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown risk profile"):
        get_profile("YOLO")


def test_list_profiles_preserves_ui_order() -> None:
    assert [profile.name for profile in list_profiles()] == [
        ProfileName.CONSERVATIVE,
        ProfileName.BALANCED,
        ProfileName.AGGRESSIVE,
    ]


def test_risk_profile_rejects_invalid_fraction() -> None:
    with pytest.raises(ValueError, match="between 0 and 1"):
        RiskProfile(
            name=ProfileName.BALANCED,
            max_strategy_concentration=1.2,
            max_bridge_exposure=0.25,
            max_entry_exit_slippage=0.01,
            max_portfolio_lp_il_stress=0.05,
            max_exit_time_days=30,
            max_slashing_stress_loss=0.05,
        )


def test_risk_profile_rejects_nonpositive_exit_time() -> None:
    with pytest.raises(ValueError, match="> 0"):
        RiskProfile(
            name=ProfileName.BALANCED,
            max_strategy_concentration=0.60,
            max_bridge_exposure=0.25,
            max_entry_exit_slippage=0.01,
            max_portfolio_lp_il_stress=0.05,
            max_exit_time_days=0,
            max_slashing_stress_loss=0.05,
        )
