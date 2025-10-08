"""
Authentication helpers and session derivation.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import get_settings


auth_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class SessionContext:
    """Holds derived session information for sandbox routing."""

    id: str
    token: Optional[str]


def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(auth_scheme),
) -> Optional[str]:
    """Validate bearer token if configured and return the token value."""

    settings = get_settings()
    expected = settings.auth_token

    if expected:
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
        if credentials.credentials != expected:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    return credentials.credentials if credentials else None


def session_dependency(
    request: Request,
    token: Optional[str] = Depends(require_auth),
) -> SessionContext:
    """Derive a session identifier from headers or auth token."""

    explicit = request.headers.get("X-Session-ID")
    if explicit:
        session_id = explicit.strip()
    else:
        seed = token
        if not seed:
            client_host = getattr(request.client, "host", None)
            seed = client_host or "anonymous"
        session_id = hashlib.sha256(seed.encode("utf-8")).hexdigest()

    return SessionContext(id=session_id, token=token)
