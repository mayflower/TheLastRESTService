"""
Sandbox manager responsible for coordinating with the isolated execution environment.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, MutableMapping, Optional

from .errors import SandboxExecutionError

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SandboxResponse:
    """Structure returned from sandbox execution."""

    status: int
    body: Any | None
    headers: Optional[Dict[str, str]] = None
    media_type: Optional[str] = None
    is_json: bool = True


@dataclass(slots=True)
class SessionState:
    """In-memory representation of a sandbox session."""

    session_id: str
    session_bytes: Optional[bytes] = None
    session_metadata: Optional[Dict[str, Any]] = field(default_factory=dict)


@dataclass(slots=True)
class DriverResult:
    """Result structure returned by the sandbox driver call."""

    status: int
    headers: Dict[str, str]
    body: Any | None
    media_type: Optional[str]
    is_json: bool
    session_bytes: Optional[bytes]
    session_metadata: Optional[Dict[str, Any]]


class SandboxAdapter:
    """Abstract adapter for communicating with the actual sandbox runtime."""

    async def execute(
        self,
        ctx: Mapping[str, Any],
        state: SessionState,
    ) -> DriverResult:
        raise NotImplementedError


class StubSandboxAdapter(SandboxAdapter):
    """Placeholder adapter until the real sandbox bridge is implemented."""

    async def execute(self, ctx: Mapping[str, Any], state: SessionState) -> DriverResult:
        await asyncio.sleep(0)
        return DriverResult(
            status=501,
            headers={},
            body={
                "error": "Sandbox integration pending",
                "reason": "No sandbox backend wired",
                "path": ctx.get("path"),
            },
            media_type=None,
            is_json=True,
            session_bytes=state.session_bytes,
            session_metadata=state.session_metadata,
        )


class SandboxManager:
    """Facade for executing plans inside the sandbox environment."""

    def __init__(self, adapter: Optional[SandboxAdapter] = None) -> None:
        self._adapter = adapter or StubSandboxAdapter()
        self._sessions: MutableMapping[str, SessionState] = {}

    def _get_session(self, session_id: str) -> SessionState:
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionState(session_id=session_id)
        return self._sessions[session_id]

    async def execute_planned(self, ctx: Dict[str, Any]) -> SandboxResponse:
        session = ctx.get("session") or {}
        session_id = session.get("id")
        if not session_id:
            raise SandboxExecutionError("Session identifier missing from context", status_code=400)

        state = self._get_session(session_id)

        try:
            result = await self._adapter.execute(ctx, state)
        except SandboxExecutionError:
            raise
        except NotImplementedError as exc:
            raise SandboxExecutionError("Sandbox integration missing", status_code=501) from exc
        except Exception as exc:
            logger.exception("sandbox_adapter_failure", extra={"session_id": session_id})
            raise SandboxExecutionError("Sandbox adapter failure") from exc

        state.session_bytes = result.session_bytes
        state.session_metadata = result.session_metadata

        headers = dict(result.headers)
        if result.is_json and isinstance(result.body, (dict, list)):
            body = result.body
        elif result.body is None:
            body = None
        else:
            body = result.body

        return SandboxResponse(
            status=result.status,
            body=body,
            headers=headers,
            media_type=result.media_type,
            is_json=result.is_json,
        )
