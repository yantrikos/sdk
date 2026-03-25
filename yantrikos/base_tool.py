"""
BaseTool — The foundation of every Yantrikos tool.

Every tool MUST declare tier-aware descriptions and parameters.
The SDK enforces this at registration time.

Usage:
    from yantrikos import BaseTool, ToolResult, Tier

    class MyTool(BaseTool):
        name = "my_tool"
        category = "general"

        descriptions = {
            Tier.S:  "Short desc",
            Tier.M:  "Medium description",
            Tier.L:  "Longer description with details",
            Tier.XL: "Full description with all context and examples",
        }

        parameters = {
            Tier.S:  {"query": str},
            Tier.M:  {"query": str, "limit": int},
            Tier.L:  {"query": str, "limit": int, "format": str},
            Tier.XL: {"query": str, "limit": int, "format": str, "verbose": bool},
        }

        def execute(self, input: dict, tier: Tier) -> ToolResult:
            query = input["query"]
            if tier == Tier.S:
                return ToolResult.ok(basic_search(query))
            else:
                return ToolResult.ok(full_search(query, **input))
"""

import time
import logging
from typing import Optional, Any, ClassVar

from yantrikos.tier import Tier, get_tier_config
from yantrikos.result import ToolResult
from yantrikos.errors import ToolValidationError, TierMissingError, ParameterError

logger = logging.getLogger("yantrikos.tool")


class BaseTool:
    """
    Abstract base for all Yantrikos tools.

    Subclasses MUST define:
    - name: str
    - descriptions: dict[Tier, str]
    - parameters: dict[Tier, dict]
    - execute(input, tier) -> ToolResult

    Optional:
    - category: str (default "general")
    - embedding_text: str (custom text for similarity matching)
    - validate_input(input, tier) -> list[str] (custom validation)
    """

    # Required class attributes
    name: ClassVar[str] = ""
    category: ClassVar[str] = "general"
    descriptions: ClassVar[dict] = {}
    parameters: ClassVar[dict] = {}
    embedding_text: ClassVar[str] = ""

    def execute(self, input: dict, tier: Tier) -> ToolResult:
        """Execute the tool. Must be overridden."""
        raise NotImplementedError(f"{self.__class__.__name__}.execute() not implemented")

    # ── Tier-Aware Accessors ───────────────────────────────────────

    def get_description(self, tier: Tier) -> str:
        """Get description for a specific tier. Falls back to nearest higher tier."""
        if tier in self.descriptions:
            return self.descriptions[tier]
        # Fallback chain: S -> M -> L -> XL
        for fallback in [Tier.M, Tier.L, Tier.XL]:
            if fallback in self.descriptions:
                desc = self.descriptions[fallback]
                config = get_tier_config(tier)
                max_chars = config["max_description_chars"]
                if max_chars and len(desc) > max_chars:
                    return desc[:max_chars - 3] + "..."
                return desc
        return self.name

    def get_parameters(self, tier: Tier) -> dict:
        """Get parameters for a specific tier. Falls back to nearest lower tier."""
        if tier in self.parameters:
            return self.parameters[tier]
        # Fallback chain: try lower tiers first (simpler is safer)
        for fallback in [Tier.S, Tier.M, Tier.L, Tier.XL]:
            if fallback in self.parameters:
                return self.parameters[fallback]
        return {}

    def get_embedding_text(self) -> str:
        """Get text optimized for embedding similarity matching."""
        if self.embedding_text:
            return self.embedding_text
        # Combine name + longest description for best embedding
        longest = max(self.descriptions.values(), key=len) if self.descriptions else ""
        return f"{self.name}: {longest}"

    # ── Validation ─────────────────────────────────────────────────

    def validate_input(self, input: dict, tier: Tier) -> list[str]:
        """
        Validate input against tier parameters.
        Override for custom validation. Returns list of errors (empty = valid).

        Convention: only the FIRST parameter is strictly required.
        All others are optional with sensible defaults in the tool implementation.
        """
        errors = []
        params = self.get_parameters(tier)
        param_names = list(params.keys())

        # Only first param is required
        if param_names and param_names[0] not in input:
            errors.append(f"Missing required parameter: {param_names[0]}")

        return errors

    def safe_execute(self, input: dict, tier: Tier) -> ToolResult:
        """Execute with validation, error handling, and timing."""
        # Validate
        errors = self.validate_input(input, tier)
        if errors:
            return ToolResult.fail(f"Validation: {'; '.join(errors)}")

        # Execute with timing
        start = time.monotonic()
        try:
            result = self.execute(input, tier)
            result.duration_ms = int((time.monotonic() - start) * 1000)
            return result
        except Exception as e:
            duration = int((time.monotonic() - start) * 1000)
            logger.error("Tool %s failed: %s", self.name, e)
            return ToolResult(success=False, error=str(e), duration_ms=duration)

    # ── Serialization ──────────────────────────────────────────────

    def to_schema(self, tier: Tier) -> dict:
        """Export as a JSON-serializable tool schema for the given tier."""
        return {
            "name": self.name,
            "description": self.get_description(tier),
            "category": self.category,
            "parameters": {
                k: (v.__name__ if isinstance(v, type) else str(v))
                for k, v in self.get_parameters(tier).items()
            },
        }

    def to_full_schema(self) -> dict:
        """Export full schema with all tiers."""
        return {
            "name": self.name,
            "category": self.category,
            "embedding_text": self.get_embedding_text(),
            "tiers": {
                tier.value: {
                    "description": self.get_description(tier),
                    "parameters": {
                        k: (v.__name__ if isinstance(v, type) else str(v))
                        for k, v in self.get_parameters(tier).items()
                    },
                }
                for tier in Tier
            },
        }

    # ── Class Validation ───────────────────────────────────────────

    @classmethod
    def validate_class(cls) -> list[str]:
        """Validate that the tool class is properly defined."""
        errors = []

        if not cls.name:
            errors.append(f"{cls.__name__}: 'name' is required")

        if not cls.descriptions:
            errors.append(f"{cls.__name__}: 'descriptions' dict is required")
        else:
            for tier in Tier:
                if tier not in cls.descriptions:
                    errors.append(f"{cls.__name__}: missing description for Tier.{tier.name}")

        if not cls.parameters:
            errors.append(f"{cls.__name__}: 'parameters' dict is required")
        else:
            # S tier must have fewest params
            s_count = len(cls.parameters.get(Tier.S, {}))
            xl_count = len(cls.parameters.get(Tier.XL, {}))
            if s_count > xl_count and xl_count > 0:
                errors.append(f"{cls.__name__}: Tier.S has more params ({s_count}) than Tier.XL ({xl_count})")

        return errors

    def __repr__(self):
        return f"<{self.__class__.__name__} name={self.name} category={self.category}>"
