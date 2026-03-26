"""
TierRouter — The core routing engine for tier-based tool presentation.

This is what the Tier OpenClaw plugin uses to decide which tools
to present and how, based on detected model tier.

Strategies (from whitepaper benchmarks):
- Tier S/M: hybrid (K detailed + rest name-only) — best for small models
- Tier L: semantic reorder + category hint — best for large models
- Tier XL: full tool set — no adaptation needed
"""

from typing import Optional, Callable
from yantrikos.base_tool import BaseTool
from yantrikos.tier import Tier, get_tier_config
from yantrikos.detect import detect_tier, detect_model_family
from yantrikos.native import to_native_tool, to_native_tool_nameonly, to_native_tools
from yantrikos.registry import all_tools, by_category, categories


class TierRouter:
    """
    Routes tool presentation based on model tier.

    Usage:
        router = TierRouter(model_name="qwen2.5:1.5b")
        native_tools = router.route(user_prompt="Read the file config.yaml")
        # Returns Ollama/OpenAI native tool definitions, adapted for 1.5B
    """

    def __init__(
        self,
        model_name: str = "",
        tier: Optional[Tier] = None,
        ranker: Optional[Callable] = None,
        detailed_k: int = 8,
    ):
        """
        Args:
            model_name: Model identifier for auto tier detection
            tier: Override detected tier
            ranker: Optional callable(query, tools, k) -> ranked_tools for semantic ranking
            detailed_k: Number of tools to give full descriptions in hybrid mode
        """
        self.model_name = model_name
        self.tier = tier or detect_tier(model_name)
        self.family = detect_model_family(model_name)
        self.ranker = ranker
        self.detailed_k = detailed_k
        self._config = get_tier_config(self.tier)

    def route(self, user_prompt: str, tools: Optional[list[BaseTool]] = None) -> list[dict]:
        """
        Route tools for a given user prompt. Returns native tool definitions.

        Strategy selection based on whitepaper findings:
        - Tier.S:  hybrid (K detailed + rest name-only)
        - Tier.M:  hybrid (K detailed + rest name-only)
        - Tier.L:  all tools, semantically reordered
        - Tier.XL: all tools, original order
        """
        if tools is None:
            tools = all_tools()

        if not tools:
            return []

        if self.tier == Tier.XL:
            return self._strategy_full(tools)
        elif self.tier == Tier.L:
            return self._strategy_reorder(tools, user_prompt)
        else:  # S or M
            return self._strategy_hybrid(tools, user_prompt)

    def route_with_hint(self, user_prompt: str,
                        tools: Optional[list[BaseTool]] = None) -> tuple[list[dict], str]:
        """
        Route tools AND return a system prompt hint.
        Returns (native_tools, system_hint).
        """
        native = self.route(user_prompt, tools)

        if self.tier in (Tier.S, Tier.M):
            hint = ""  # MCQ/hybrid doesn't need a hint
        elif self.tier == Tier.L:
            cats = categories()
            hint = (
                f"Tools are organized in categories: {', '.join(cats)}. "
                "Identify the relevant category first, then pick the best tool."
            )
        else:
            hint = ""

        return native, hint

    # ── Strategies ─────────────────────────────────────────────────

    def _strategy_full(self, tools: list[BaseTool]) -> list[dict]:
        """XL: all tools, full descriptions."""
        return [to_native_tool(t, self.tier) for t in tools]

    def _strategy_reorder(self, tools: list[BaseTool], prompt: str) -> list[dict]:
        """L: all tools, semantically reordered (most relevant first)."""
        if self.ranker:
            ranked = self.ranker(prompt, tools, len(tools))
            ranked_names = {t.name for t in ranked}
            # Ranked tools first, then remaining
            ordered = list(ranked)
            for t in tools:
                if t.name not in ranked_names:
                    ordered.append(t)
            return [to_native_tool(t, self.tier) for t in ordered]
        else:
            # No ranker: use full set as-is
            return [to_native_tool(t, self.tier) for t in tools]

    def _strategy_hybrid(self, tools: list[BaseTool], prompt: str) -> list[dict]:
        """S/M: top-K get full descriptions, rest get name-only."""
        if self.ranker:
            detailed = self.ranker(prompt, tools, self.detailed_k)
            detailed_names = {t.name for t in detailed}
        else:
            # No ranker: first K tools by category match
            detailed_names = {t.name for t in tools[:self.detailed_k]}

        native = []
        # Detailed tools first
        for t in tools:
            if t.name in detailed_names:
                native.append(to_native_tool(t, self.tier))
        # Then name-only for the rest
        for t in tools:
            if t.name not in detailed_names:
                native.append(to_native_tool_nameonly(t))
        return native

    # ── Info ────────────────────────────────────────────────────────

    def info(self) -> dict:
        """Return router configuration info."""
        return {
            "model_name": self.model_name,
            "tier": self.tier.value,
            "family": self.family,
            "strategy": self._get_strategy_name(),
            "detailed_k": self.detailed_k,
            "has_ranker": self.ranker is not None,
            "config": self._config,
        }

    def _get_strategy_name(self) -> str:
        if self.tier == Tier.XL:
            return "full"
        elif self.tier == Tier.L:
            return "reorder"
        else:
            return "hybrid"
