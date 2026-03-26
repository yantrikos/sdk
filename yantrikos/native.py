"""
Native tool format — export tools as OpenAI/Ollama native tool calling schemas.

This is the bridge between the Yantrikos SDK and production tool calling APIs.
"""

from typing import Optional
from yantrikos.base_tool import BaseTool
from yantrikos.tier import Tier


# Python type -> JSON Schema type mapping
_TYPE_MAP = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}


def to_native_tool(tool: BaseTool, tier: Tier) -> dict:
    """
    Export a tool as an OpenAI/Ollama native tool definition.

    Returns the format expected by /api/chat tools parameter:
    {
        "type": "function",
        "function": {
            "name": "tool_name",
            "description": "Tool description for this tier",
            "parameters": {
                "type": "object",
                "properties": {...},
                "required": [...]
            }
        }
    }
    """
    params = tool.get_parameters(tier)
    properties = {}
    required = []

    for i, (name, ptype) in enumerate(params.items()):
        json_type = _TYPE_MAP.get(ptype, "string") if isinstance(ptype, type) else "string"
        properties[name] = {
            "type": json_type,
            "description": name.replace("_", " "),
        }
        # First param is always required; others optional
        if i == 0:
            required.append(name)

    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.get_description(tier),
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }


def to_native_tool_nameonly(tool: BaseTool) -> dict:
    """
    Export a tool as a minimal name-only native tool definition.
    Used for the "72 name-only" portion of hybrid presentation.
    """
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.name.replace("_", " "),
            "parameters": {"type": "object", "properties": {}},
        },
    }


def to_native_tools(tools: list[BaseTool], tier: Tier,
                     detailed_names: Optional[set[str]] = None) -> list[dict]:
    """
    Export a list of tools as native tool definitions.

    If detailed_names is provided, those tools get full tier descriptions
    and the rest get name-only (hybrid mode).
    """
    native = []
    for tool in tools:
        if detailed_names is None or tool.name in detailed_names:
            native.append(to_native_tool(tool, tier))
        else:
            native.append(to_native_tool_nameonly(tool))
    return native
