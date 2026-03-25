"""Tool execution results."""

from dataclasses import dataclass, field
from typing import Optional, Any


@dataclass
class ToolResult:
    """Result of a tool execution."""
    success: bool = True
    output: Any = None
    error: Optional[str] = None
    duration_ms: int = 0
    metadata: dict = field(default_factory=dict)

    @staticmethod
    def ok(output: Any, **metadata) -> "ToolResult":
        return ToolResult(success=True, output=output, metadata=metadata)

    @staticmethod
    def fail(error: str, **metadata) -> "ToolResult":
        return ToolResult(success=False, error=error, metadata=metadata)
