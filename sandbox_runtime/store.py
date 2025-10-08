"""Resource storage utilities for JSON-backed entity collections."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Iterable, List, Optional, Tuple


def _normalize_identifier(value: Any) -> Any:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        trimmed = value.strip()
        if trimmed.isdigit() and (not trimmed.startswith("0") or trimmed == "0"):
            return int(trimmed)
        return trimmed
    return value


class SessionStore:
    """Session-level storage namespace per tenant."""

    def __init__(self, session_state: Dict[str, Any], tenant_id: str) -> None:
        self._session_state = session_state
        tenants = session_state.setdefault("tenants", {})
        self._tenant_state: Dict[str, Any] = tenants.setdefault(tenant_id, {})

    def resource(self, resource_name: str) -> "ResourceStore":
        return ResourceStore(self._tenant_state, resource_name)

    def snapshot(self) -> Dict[str, Any]:
        return self._session_state


class ResourceStore:
    """JSON-like collection management scoped to a resource name."""

    def __init__(self, tenant_state: Dict[str, Any], resource_name: str) -> None:
        self._tenant_state = tenant_state
        self._resource_name = resource_name
        resource_state = tenant_state.setdefault(resource_name, {})
        self._items: List[Dict[str, Any]] = resource_state.setdefault("items", [])
        self._auto_id: int = int(resource_state.get("auto_id", 1))
        resource_state["auto_id"] = self._auto_id
        self._resource_state = resource_state

    def _update_auto_id(self, candidate: int) -> None:
        if candidate >= self._auto_id:
            self._auto_id = candidate + 1
            self._resource_state["auto_id"] = self._auto_id

    def _next_id(self) -> int:
        existing_ids = [item.get("id") for item in self._items if isinstance(item.get("id"), int)]
        max_existing = max(existing_ids or [0])
        next_id = max(self._auto_id, max_existing + 1)
        self._auto_id = next_id + 1
        self._resource_state["auto_id"] = self._auto_id
        return next_id

    def _find_index(self, identifier: Any) -> Optional[int]:
        target = _normalize_identifier(identifier)
        for index, record in enumerate(self._items):
            record_id = record.get("id")
            if _normalize_identifier(record_id) == target:
                return index
        return None

    def insert(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        record = deepcopy(obj)
        if "id" in record and record["id"] is not None:
            existing_id = record["id"]
            normalized = _normalize_identifier(existing_id)
            if self._find_index(normalized) is not None:
                raise ValueError("Resource with identifier already exists")
            if isinstance(normalized, int):
                record["id"] = normalized
                self._update_auto_id(normalized)
            else:
                record["id"] = existing_id
        else:
            record_id = self._next_id()
            record["id"] = record_id

        self._items.append(deepcopy(record))
        return deepcopy(record)

    def get(self, identifier: Any) -> Optional[Dict[str, Any]]:
        index = self._find_index(identifier)
        if index is None:
            return None
        return deepcopy(self._items[index])

    def delete(self, identifier: Any) -> bool:
        index = self._find_index(identifier)
        if index is None:
            return False
        self._items.pop(index)
        return True

    def replace(self, identifier: Any, obj: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        index = self._find_index(identifier)
        if index is None:
            return None

        existing = self._items[index]
        record = deepcopy(obj)
        record["id"] = existing.get("id")
        self._items[index] = deepcopy(record)
        return deepcopy(record)

    def update(self, identifier: Any, changes: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        index = self._find_index(identifier)
        if index is None:
            return None
        existing = deepcopy(self._items[index])
        for key, value in changes.items():
            if key == "id":
                continue
            existing[key] = value
        self._items[index] = deepcopy(existing)
        return deepcopy(existing)

    def list(
        self,
        *,
        limit: Optional[int] = None,
        offset: int = 0,
        sort: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        items = [deepcopy(item) for item in self._items]
        if sort:
            reverse = sort.startswith("-")
            field = sort[1:] if reverse else sort
            items.sort(key=lambda item: item.get(field), reverse=reverse)

        total = len(items)
        if offset:
            offset = max(offset, 0)
            items = items[offset:]
        if limit is not None:
            limit = max(limit, 0)
            items = items[:limit]
        return items, total

    def search(self, criteria: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        results = [deepcopy(item) for item in self._items]
        for key, raw_value in criteria.items():
            if raw_value is None:
                continue
            value = raw_value
            if isinstance(value, list):
                value = value[-1]

            if key in {"limit", "offset", "sort"}:
                continue

            if key.endswith("__contains"):
                field = key[:-10]
                value_str = str(value)
                results = [
                    item for item in results if value_str in str(item.get(field, ""))
                ]
            elif key.endswith("__icontains"):
                field = key[:-11]
                value_str = str(value).lower()
                results = [
                    item
                    for item in results
                    if value_str in str(item.get(field, "")).lower()
                ]
            else:
                results = [item for item in results if item.get(key) == value]

        return results
