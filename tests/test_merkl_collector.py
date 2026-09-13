"""Tests for Merkl campaign-only incentive extraction."""

import pytest

from src.ascend_optimizer.collectors.merkl import (
    fetch_merkl_pool_incentive,
    parse_merkl_campaign_incentive,
)


POOL = "0x1111111111111111111111111111111111111111"


def test_merkl_uses_campaign_breakdowns_not_total_apr() -> None:
    payload = [
        {
            "identifier": POOL,
            "status": "LIVE",
            "apr": 15.0,
            "aprRecord": {
                "cumulated": 15.0,
                "breakdowns": [
                    {
                        "identifier": "native",
                        "type": "PROTOCOL",
                        "value": 10.0,
                    },
                    {
                        "identifier": "campaign-a",
                        "type": "CAMPAIGN",
                        "value": 5.0,
                    },
                ],
            },
        }
    ]

    result = parse_merkl_campaign_incentive(
        payload,
        pool_address=POOL,
    )

    assert result.campaign_apr == pytest.approx(0.05)
    assert result.incentive_apy > result.campaign_apr
    assert result.matched_campaigns == 1


def test_merkl_deduplicates_same_campaign_across_opportunities() -> None:
    payload = [
        {
            "identifier": POOL,
            "status": "LIVE",
            "aprRecord": {
                "breakdowns": [
                    {
                        "identifier": "campaign-a",
                        "type": "CAMPAIGN",
                        "value": 4.0,
                    }
                ]
            },
        },
        {
            "identifier": POOL.upper(),
            "status": "LIVE",
            "aprRecord": {
                "breakdowns": [
                    {
                        "identifier": "campaign-a",
                        "type": "CAMPAIGN",
                        "value": 4.0,
                    },
                    {
                        "identifier": "campaign-b",
                        "type": "CAMPAIGN",
                        "value": 1.0,
                    },
                ]
            },
        },
    ]

    result = parse_merkl_campaign_incentive(
        payload,
        pool_address=POOL,
    )

    assert result.campaign_apr == pytest.approx(0.05)
    assert result.matched_opportunities == 2
    assert result.matched_campaigns == 2


def test_merkl_no_matching_live_campaign_returns_zero() -> None:
    payload = [
        {
            "identifier": POOL,
            "status": "PAST",
            "aprRecord": {
                "breakdowns": [
                    {
                        "identifier": "campaign-a",
                        "type": "CAMPAIGN",
                        "value": 8.0,
                    }
                ]
            },
        }
    ]

    result = parse_merkl_campaign_incentive(
        payload,
        pool_address=POOL,
    )

    assert result.campaign_apr == 0
    assert result.incentive_apy == 0
    assert result.matched_campaigns == 0


def test_fetch_merkl_uses_pool_identifier_and_chain() -> None:
    captured = {}

    def fake_json(url, headers=None):
        captured["url"] = url
        return []

    result = fetch_merkl_pool_incentive(
        POOL,
        json_fn=fake_json,
    )

    assert "chainId=16661" in captured["url"]
    assert "identifier=0x1111111111111111111111111111111111111111" in captured["url"]
    assert result.incentive_apy == 0
