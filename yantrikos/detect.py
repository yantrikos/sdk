"""
Model tier detection — auto-detect capability tier from model name.

Based on ModelCapabilityProfile from YantrikOS (capability.rs).
Handles Ollama tag format, HuggingFace format, and cloud model names.
"""

import re
from typing import Optional
from yantrikos.tier import Tier


def detect_tier(model_name: str) -> Tier:
    """
    Detect model tier from name string.

    Examples:
        detect_tier("qwen3.5:0.6b")     -> Tier.S
        detect_tier("qwen2.5:1.5b")     -> Tier.S
        detect_tier("qwen3.5:9b")       -> Tier.M
        detect_tier("Qwen3.5-9B")       -> Tier.M
        detect_tier("gpt-oss:20b")      -> Tier.L
        detect_tier("qwen3.5:35b")      -> Tier.XL
        detect_tier("claude-opus-4-6")   -> Tier.XL
        detect_tier("gpt-4o")           -> Tier.XL
    """
    params = extract_param_count(model_name)

    if params is not None:
        if params < 4.0:
            return Tier.S
        elif params < 14.0:
            return Tier.M
        elif params < 35.0:
            return Tier.L
        else:
            return Tier.XL

    # Cloud models -> XL
    lower = model_name.lower()
    if any(name in lower for name in ("claude", "gpt-4", "gpt-5", "gemini", "o1", "o3", "o4")):
        return Tier.XL

    # Unknown -> M (safe default)
    return Tier.M


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
