"""
Model tier detection — auto-detect capability tier from model name or parameter count.

Based on ModelCapabilityProfile from YantrikOS (capability.rs).
Supports: Ollama API (model_info.general.parameter_count), name parsing, cloud models.
"""

import re
import json
import urllib.request
from typing import Optional
from yantrikos.tier import Tier


def detect_tier(model_name: str, parameter_count: Optional[int] = None) -> Tier:
    """
    Detect model tier from name string or exact parameter count.

    Args:
        model_name: Model identifier (e.g., "qwen3.5:9b", "claude-opus-4-6")
        parameter_count: Exact parameter count (e.g., 9653104368). Takes priority over name parsing.

    Examples:
        detect_tier("qwen3.5:0.6b")                -> Tier.S
        detect_tier("qwen2.5:1.5b")                -> Tier.S
        detect_tier("qwen3.5:9b")                  -> Tier.M
        detect_tier("gpt-oss:20b")                 -> Tier.L
        detect_tier("qwen3.5:35b")                 -> Tier.XL
        detect_tier("claude-opus-4-6")              -> Tier.XL
        detect_tier("custom", parameter_count=9_653_104_368)  -> Tier.M
    """
    # Use exact parameter count if provided
    if parameter_count is not None:
        return _tier_from_param_count(parameter_count / 1e9)

    # Try name-based detection
    params = extract_param_count(model_name)
    if params is not None:
        return _tier_from_param_count(params)

    # Cloud models -> XL
    lower = model_name.lower()
    if any(name in lower for name in ("claude", "gpt-4", "gpt-5", "gemini", "o1", "o3", "o4")):
        return Tier.XL

    # Unknown -> M (safe default)
    return Tier.M


def detect_tier_from_ollama(model_name: str, host: str = "http://localhost:11434") -> Tier:
    """
    Detect tier by querying Ollama's /api/show for exact parameter count.

    Uses model_info."general.parameter_count" which is available for all
    local text models served by Ollama.

    Args:
        model_name: Ollama model name (e.g., "qwen3.5:9b")
        host: Ollama API host (default: http://localhost:11434)

    Returns:
        Detected Tier

    Raises:
        ConnectionError: If Ollama is not reachable
    """
    param_count = get_ollama_parameter_count(model_name, host)
    if param_count is not None:
        return _tier_from_param_count(param_count / 1e9)
    # Fallback to name parsing
    return detect_tier(model_name)


def get_ollama_parameter_count(model_name: str, host: str = "http://localhost:11434") -> Optional[int]:
    """
    Query Ollama /api/show for the exact parameter count.

    Returns the raw parameter count (e.g., 9653104368 for a 9B model)
    or None if unavailable.
    """
    try:
        payload = json.dumps({"model": model_name}).encode()
        req = urllib.request.Request(
            f"{host}/api/show",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
        model_info = data.get("model_info", {})
        count = model_info.get("general.parameter_count")
        if count is not None:
            return int(count)
    except Exception:
        pass
    return None


def detect_tier_from_openrouter(model_id: str, api_key: str) -> Tier:
    """
    Detect tier by querying OpenRouter's /api/v1/models for parameter count.

    Args:
        model_id: OpenRouter model ID (e.g., "qwen/qwen3.5-9b", "meta-llama/llama-3-8b")
        api_key: OpenRouter API key

    Returns:
        Detected Tier
    """
    param_count = get_openrouter_parameter_count(model_id, api_key)
    if param_count is not None:
        return _tier_from_param_count(param_count / 1e9)
    # Fallback: extract from model ID string
    return detect_tier(model_id)


def get_openrouter_parameter_count(model_id: str, api_key: str) -> Optional[int]:
    """
    Query OpenRouter /api/v1/models for parameter count.

    Returns raw parameter count or None if unavailable.
    """
    try:
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/models",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        for model in data.get("data", []):
            if model.get("id") == model_id:
                # OpenRouter stores parameter count in architecture.num_parameters
                arch = model.get("architecture", {})
                num_params = arch.get("num_parameters")
                if num_params is not None:
                    return int(num_params)
                # Fallback: parse from model name/context
                break
    except Exception:
        pass
    return None


def detect_tier_auto(
    model_name: str,
    ollama_host: Optional[str] = None,
    openrouter_key: Optional[str] = None,
) -> Tier:
    """
    Auto-detect tier using the best available method.

    Tries in order:
    1. Ollama API (if host provided or localhost available)
    2. OpenRouter API (if key provided)
    3. Name parsing (always available)
    4. Cloud model detection (claude, gpt-4, gemini → XL)

    Args:
        model_name: Model identifier
        ollama_host: Ollama API host (tries localhost if None)
        openrouter_key: OpenRouter API key

    Examples:
        detect_tier_auto("qwen3.5:9b")                           # Ollama local
        detect_tier_auto("qwen/qwen3.5-9b", openrouter_key="sk-or-...")  # OpenRouter
        detect_tier_auto("claude-opus-4-6")                       # Cloud → XL
    """
    # Try Ollama
    host = ollama_host or "http://localhost:11434"
    count = get_ollama_parameter_count(model_name, host)
    if count is not None:
        return _tier_from_param_count(count / 1e9)

    # Try OpenRouter
    if openrouter_key:
        count = get_openrouter_parameter_count(model_name, openrouter_key)
        if count is not None:
            return _tier_from_param_count(count / 1e9)

    # Fallback to name parsing
    return detect_tier(model_name)


def _tier_from_param_count(params_b: float) -> Tier:
    """Classify tier from parameter count in billions."""
    if params_b < 4.0:
        return Tier.S
    elif params_b < 14.0:
        return Tier.M
    elif params_b < 35.0:
        return Tier.L
    else:
        return Tier.XL


def extract_param_count(model_name: str) -> Optional[float]:
    """
    Extract parameter count in billions from model name.

    Handles:
      - Ollama tag: "qwen3.5:9b", "qwen3.5:0.6b", "qwen3.5:27b-nothink"
      - HuggingFace: "Qwen3.5-9B", "Llama-3.2-1B", "phi-3-mini-4k-3.8b"
      - Generic: any string containing a number followed by 'b' or 'B'
    """
    lower = model_name.lower()

    # Pattern 1: Ollama tag format — ":Xb" (e.g., "qwen3.5:27b-nothink")
    colon = lower.rfind(":")
    if colon >= 0:
        after = lower[colon + 1:]
        m = re.match(r"(\d+\.?\d*)b", after)
        if m:
            val = float(m.group(1))
            if 0 < val < 1000:
                return val

    # Pattern 2: HuggingFace format — "-XB" or "_XB" (e.g., "Qwen3.5-9B")
    for sep in ("-", "_"):
        for part in lower.split(sep):
            if part.endswith("b") and len(part) > 1:
                try:
                    val = float(part[:-1])
                    if 0 < val < 1000:
                        return val
                except ValueError:
                    continue

    return None


def detect_model_family(model_name: str) -> str:
    """
    Detect model family for chat template selection.

    Returns: "qwen", "llama", "nemotron", "gemma", "phi", "openai", "anthropic", "generic"
    """
    lower = model_name.lower()

    if "qwen" in lower or lower.startswith("yantrik"):
        return "qwen"
    elif "nemotron" in lower:
        return "nemotron"
    elif "llama" in lower or "codellama" in lower:
        return "llama"
    elif "gemma" in lower:
        return "gemma"
    elif "phi" in lower:
        return "phi"
    elif "gpt-" in lower or "o1" in lower or "o3" in lower or "o4" in lower:
        return "openai"
    elif "claude" in lower:
        return "anthropic"
    else:
        return "generic"
