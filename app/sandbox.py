"""Sandbox manager placeholder; implementation provided in a later step."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .errors import SandboxExecutionError


@dataclass(slots=True)
class SandboxResponse:
    """Structure returned from sandbox execution."""

    status: int
    body: Any | None
    headers: Optional[Dict[str, str]] = None
    media_type: Optional[str] = None
    is_json: bool = True


class SandboxManager:
    """Facade for executing plans inside the sandbox environment."""

    async def execute_planned(self, ctx: Dict[str, Any]) -> SandboxResponse:
        raise SandboxExecutionError("Sandbox execution not yet implemented", status_code=501)

