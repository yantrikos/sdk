"""SDK error hierarchy."""

from typing import Optional


class YantrikosError(Exception):
    code: str = "YANTRIKOS_ERROR"
    retryable: bool = False
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message)
        self.details = details or {}


class ToolValidationError(YantrikosError):
    code = "TOOL_VALIDATION_ERROR"


class TierMissingError(ToolValidationError):
    code = "TIER_MISSING"


class ExecutionError(YantrikosError):
    code = "EXECUTION_ERROR"
    retryable = True


class ParameterError(YantrikosError):
    code = "PARAMETER_ERROR"
