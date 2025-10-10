"""Filesystem utilities for safe, sandboxed file operations."""

from __future__ import annotations

import os
from pathlib import Path


class FilesystemError(RuntimeError):
    """Raised when filesystem operations violate safety constraints."""


def get_sandbox_root() -> Path:
    """Get the root directory for all sandbox session data."""
    # Use environment variable if set, otherwise default
    root = os.environ.get("SANDBOX_DATA_ROOT", "/tmp/sandbox_data")
    path = Path(root)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_session_dir(session_id: str) -> Path:
    """Get the root directory for a specific session's data."""
    if not session_id or not isinstance(session_id, str):
        raise FilesystemError("Invalid session ID")

    # Sanitize session ID to prevent path traversal
    safe_id = "".join(c for c in session_id if c.isalnum() or c in "-_")
    if not safe_id or safe_id != session_id:
        raise FilesystemError(f"Session ID contains invalid characters: {session_id}")

    session_path = get_sandbox_root() / safe_id
    session_path.mkdir(parents=True, exist_ok=True)

    # Create .schemas subdirectory
    schemas_dir = session_path / ".schemas"
    schemas_dir.mkdir(exist_ok=True)

    return session_path


def safe_path(path: str | Path, session_id: str) -> Path:
    """
    Resolve a path and ensure it stays within the session sandbox.

    Args:
        path: Relative or absolute path within session
        session_id: Session identifier

    Returns:
        Resolved absolute path within session sandbox

    Raises:
        FilesystemError: If path escapes sandbox boundaries
    """
    session_root = get_session_dir(session_id)

    # Convert to Path and resolve
    if isinstance(path, str):
        path = Path(path)

    # If path is absolute, make it relative to session root
    if path.is_absolute():
        # Strip leading slash and treat as relative
        path = Path(*path.parts[1:])

    resolved = (session_root / path).resolve()

    # Ensure resolved path is within session_root
    try:
        resolved.relative_to(session_root)
    except ValueError:
        raise FilesystemError(f"Path '{path}' escapes sandbox boundary")

    return resolved
