"""
Yantrikos SDK — Build tier-aware tools for AI agents.

Every tool declares behavior per model tier (S/M/L/XL).
The SDK enforces tier-awareness and provides routing for deployment.

DOI: 10.5281/zenodo.19228710
"""

__version__ = "0.3.0"

from yantrikos.tier import Tier, get_tier_config, TIER_CONFIG
from yantrikos.base_tool import BaseTool
from yantrikos.result import ToolResult
from yantrikos.registry import (
    register, get, all_tools, by_category, categories,
    schemas, full_schemas, count, clear,
)
from yantrikos.errors import (
    YantrikosError, ToolValidationError, TierMissingError,
    ExecutionError, ParameterError,
)
from yantrikos.detect import (
    detect_tier, detect_tier_auto,
    detect_tier_from_ollama, get_ollama_parameter_count,
    detect_tier_from_openrouter, get_openrouter_parameter_count,
    extract_param_count, detect_model_family,
)
from yantrikos.native import to_native_tool, to_native_tool_nameonly, to_native_tools
from yantrikos.router import TierRouter
