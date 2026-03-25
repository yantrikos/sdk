"""Tier definitions — the foundation of capability-aware tooling."""

from enum import Enum


class Tier(Enum):
    """Model capability tiers. Every tool must declare behavior per tier."""
    S = "S"    # 0.5B - 3B: MCQ, minimal params, simple output
    M = "M"    # 4B - 14B: condensed descriptions, core params
    L = "L"    # 15B - 35B: full descriptions, all params
    XL = "XL"  # 35B+: unrestricted


# Tier metadata
TIER_CONFIG = {
    Tier.S: {
        "label": "Small",
        "size_range": "0.5B – 3B",
        "max_tools": 4,
        "max_description_chars": 50,
        "max_params": 2,
        "format": "mcq",
        "token_budget": 200,
    },
    Tier.M: {
        "label": "Medium",
        "size_range": "4B – 14B",
        "max_tools": 8,
        "max_description_chars": 100,
        "max_params": 5,
        "format": "condensed",
        "token_budget": 500,
    },
    Tier.L: {
        "label": "Large",
        "size_range": "15B – 35B",
        "max_tools": 20,
        "max_description_chars": 200,
        "max_params": 10,
        "format": "ranked",
        "token_budget": 1500,
    },
    Tier.XL: {
        "label": "X-Large",
        "size_range": "35B+",
        "max_tools": 0,  # unlimited
        "max_description_chars": 0,  # unlimited
        "max_params": 0,  # unlimited
        "format": "full",
        "token_budget": 0,  # unlimited
    },
}


def get_tier_config(tier: Tier) -> dict:
    return TIER_CONFIG.get(tier, TIER_CONFIG[Tier.M])
