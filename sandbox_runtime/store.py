"""Resource storage utilities for JSON-backed entity collections."""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional


class ResourceStore:
    """Placeholder store that will provide JSON persistence in the sandbox."""

    def __init__(self, base_path: str) -> None:
        self.base_path = base_path

    def insert(self, obj: Dict[str, Any]) -> Any:
        raise NotImplementedError

    def get(self, identifier: Any) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    def delete(self, identifier: Any) -> bool:
        raise NotImplementedError

    def list(self, *, limit: Optional[int] = None, offset: int = 0) -> Iterable[Dict[str, Any]]:
        raise NotImplementedError

    def search(self, criteria: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        raise NotImplementedError

