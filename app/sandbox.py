"""Sandbox manager responsible for coordinating with the isolated execution environment."""

from __future__ import annotations

import asyncio
import importlib
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
    session_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DriverResult:
    """Result structure returned by the sandbox driver call."""

    status: int
    headers: Dict[str, str]
    body: Any | None
    media_type: Optional[str]
    is_json: bool
    session_bytes: Optional[bytes]
    session_metadata: Dict[str, Any]


class SandboxAdapter:
    """Abstract adapter for communicating with the actual sandbox runtime."""

    async def execute(
        self,
        ctx: Mapping[str, Any],
        state: SessionState,
    ) -> DriverResult:
        raise NotImplementedError


class SandboxRuntime:
    """In-process sandbox runtime that loads the driver module per session."""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self._driver_module_name = "sandbox_runtime.driver"
        self._driver_module = self._load_driver_module()
        self._lock = asyncio.Lock()
        self._state: Dict[str, Any] = {}

    def _load_driver_module(self):
        try:
            return importlib.import_module(self._driver_module_name)
        except ModuleNotFoundError as exc:
            raise SandboxExecutionError("Sandbox driver module not found") from exc

    async def execute(
        self,
        ctx: Mapping[str, Any],
        incoming_state: Optional[Dict[str, Any]],
    ) -> DriverResult:
        async with self._lock:
            state = dict(incoming_state or self._state or {})
            try:
                result = await asyncio.to_thread(self._call_driver, ctx, state)
            except SandboxExecutionError:
                raise
            except Exception as exc:  # pragma: no cover - safety net
                logger.exception("sandbox_driver_exception", extra={"session_id": self.session_id})
                raise SandboxExecutionError("Sandbox driver execution failed") from exc

            return self._build_result(result)

    def _call_driver(self, ctx: Mapping[str, Any], state: Dict[str, Any]) -> Mapping[str, Any]:
        handler = getattr(self._driver_module, "handle", None)
        if handler is None:
            raise SandboxExecutionError("Sandbox driver missing handle()")
        result = handler(dict(ctx), dict(state))
        if not isinstance(result, Mapping):
            raise SandboxExecutionError("Sandbox driver returned invalid payload")
        return result

    def _build_result(self, result: Mapping[str, Any]) -> DriverResult:
        state = result.get("session_state")
        if state is None:
            state = self._state
        if not isinstance(state, dict):
            raise SandboxExecutionError("Sandbox session state must be a dictionary")
        self._state = state

        headers = result.get("headers") or {}
        if not isinstance(headers, Mapping):
            raise SandboxExecutionError("Sandbox response headers must be a mapping")

        status = int(result.get("status", 500))
        body = result.get("body")
        media_type = result.get("media_type")
        is_json = bool(result.get("is_json", media_type is None))

        try:
            session_bytes = json.dumps(self._state).encode("utf-8")
        except (TypeError, ValueError):
            session_bytes = None

        return DriverResult(
            status=status,
            headers=dict(headers),
            body=body,
            media_type=media_type,
            is_json=is_json,
            session_bytes=session_bytes,
            session_metadata=self._state,
        )


class InProcessSandboxAdapter(SandboxAdapter):
    """Adapter that executes sandbox runtime logic in-process with per-session state."""

    def __init__(self) -> None:
        self._runtimes: MutableMapping[str, SandboxRuntime] = {}

    async def execute(self, ctx: Mapping[str, Any], state: SessionState) -> DriverResult:
        runtime = self._runtimes.get(state.session_id)
        if runtime is None:
            runtime = SandboxRuntime(state.session_id)
            self._runtimes[state.session_id] = runtime
        return await runtime.execute(ctx, state.session_metadata)


class SandboxManager:
    """Facade for executing plans inside the sandbox environment."""

    def __init__(self, adapter: Optional[SandboxAdapter] = None) -> None:
        self._adapter = adapter or InProcessSandboxAdapter()
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
        except Exception as exc:
            logger.exception("sandbox_adapter_failure", extra={"session_id": session_id})
            raise SandboxExecutionError("Sandbox adapter failure") from exc

        state.session_bytes = result.session_bytes
        state.session_metadata = result.session_metadata

        headers = dict(result.headers)
        body = result.body

        return SandboxResponse(
            status=result.status,
            body=body,
            headers=headers,
            media_type=result.media_type,
            is_json=result.is_json,
        )
