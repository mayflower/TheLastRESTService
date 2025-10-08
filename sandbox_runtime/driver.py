"""Driver module executed inside the sandbox session."""

from __future__ import annotations

from typing import Any, Dict


def handle(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Entry point invoked by the host to service a request."""

    raise NotImplementedError("Sandbox driver is not yet implemented")

