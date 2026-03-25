"""
Yantrikos SDK — Build tier-aware tools for AI agents.

Every tool declares behavior per model tier (S/M/L/XL).
Small models get MCQ, large models get full tool sets.

Quick start:
    from yantrikos import BaseTool, ToolResult, Tier, register

    @register
    class MyTool(BaseTool):
        name = "my_tool"
        category = "general"
        descriptions = {
            Tier.S:  "Do thing",
            Tier.M:  "Do the thing with options",
            Tier.L:  "Do the thing with full control and options",
            Tier.XL: "Do the thing with complete control, validation, and detailed output",
        }
        parameters = {
            Tier.S:  {"input": str},
            Tier.M:  {"input": str, "format": str},
            Tier.L:  {"input": str, "format": str, "verbose": bool},
            Tier.XL: {"input": str, "format": str, "verbose": bool, "timeout": int},
        }
        def execute(self, input: dict, tier: Tier) -> ToolResult:
            return ToolResult.ok({"result": input["input"]})
"""

__version__ = "0.1.0"

from yantrikos.tier import Tier, get_tier_config, TIER_CONFIG
from yantrikos.base_tool import BaseTool
from yantrikos.result import ToolResult
from yantrikos.registry import register, get, all_tools, by_category, schemas, full_schemas
from yantrikos.errors import (
    YantrikosError, ToolValidationError, TierMissingError,
    ExecutionError, ParameterError,
)
