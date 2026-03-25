"""Tool registry — register, discover, and query tools."""

import logging
from typing import Optional, Type

from yantrikos.base_tool import BaseTool
from yantrikos.tier import Tier
from yantrikos.errors import ToolValidationError

logger = logging.getLogger("yantrikos.registry")

# Global registry
_registry: dict[str, BaseTool] = {}


def register(tool_class: Type[BaseTool]) -> Type[BaseTool]:
    """
    Register a tool class. Use as a decorator:

        @register
        class MyTool(BaseTool):
            ...
    """
    errors = tool_class.validate_class()
    if errors:
        raise ToolValidationError(
            f"Tool validation failed: {'; '.join(errors)}",
            {"tool": tool_class.__name__, "errors": errors},
        )

    instance = tool_class()
    _registry[instance.name] = instance
    logger.info("Registered tool: %s (%s)", instance.name, instance.category)
    return tool_class


def get(name: str) -> Optional[BaseTool]:
    """Get a registered tool by name."""
    return _registry.get(name)


def all_tools() -> list[BaseTool]:
    """Get all registered tools."""
    return list(_registry.values())


def by_category(category: str) -> list[BaseTool]:
    """Get tools filtered by category."""
    return [t for t in _registry.values() if t.category == category]


def categories() -> list[str]:
    """Get all registered categories."""
    return sorted(set(t.category for t in _registry.values()))


def schemas(tier: Tier) -> list[dict]:
    """Export all tool schemas for a given tier."""
    return [t.to_schema(tier) for t in _registry.values()]


def full_schemas() -> list[dict]:
    """Export all tool schemas with all tiers."""
    return [t.to_full_schema() for t in _registry.values()]


def count() -> int:
    return len(_registry)


def clear():
    """Clear the registry. Mainly for testing."""
    _registry.clear()
