"""Safety utilities for code validation inside the sandbox."""

from __future__ import annotations

from typing import Any


def validate_code(source: str) -> None:
    """Validate that the generated code complies with the sandbox policy."""

    raise NotImplementedError


def safe_exec(compiled_code: Any, globals_dict: dict[str, Any]) -> Any:
    """Execute code using sandbox safe guards."""

    raise NotImplementedError

