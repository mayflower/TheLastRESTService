"""Resource storage utilities for JSON-backed entity collections with file persistence."""

from __future__ import annotations

import builtins
import json
from collections.abc import Iterable
from copy import deepcopy
from datetime import datetime
from typing import Any

from .filesystem import FilesystemError, get_session_dir


def _normalize_identifier(value: Any) -> Any:
    """Normalize identifier to int if possible, otherwise string."""
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        trimmed = value.strip()
        if trimmed.isdigit() and (not trimmed.startswith("0") or trimmed == "0"):
            return int(trimmed)
        return trimmed
    return value


class SessionStore:
    """
    Session-level storage namespace per tenant.

    Maintains file-based storage for all resources within a session.
    """

    def __init__(self, session_id: str) -> None:
        """
        Initialize session store.

        Args:
            session_id: Unique session identifier
        """
        self._session_id = session_id
        try:
            self._session_dir = get_session_dir(session_id)
        except FilesystemError as exc:
            raise ValueError(f"Invalid session: {exc}") from exc

    def resource(self, resource_name: str) -> ResourceStore:
        """
        Get a ResourceStore for a specific resource type.

        Args:
            resource_name: Name of the resource collection (e.g., "users", "products")

        Returns:
            ResourceStore instance for the specified resource
        """
        return ResourceStore(self._session_id, resource_name)

    def snapshot(self) -> dict[str, Any]:
        """
        Get a snapshot of all session data (for backward compatibility).

        Returns:
            Dictionary with session metadata
        """
        return {
            "session_id": self._session_id,
            "session_dir": str(self._session_dir),
        }


class ResourceStore:
    """
    File-backed JSON collection management scoped to a resource name.

    Data is stored in: /sandbox_data/<session>/<resource>.json
    Schema metadata in: /sandbox_data/<session>/.schemas/<resource>.json
    """

    def __init__(self, session_id: str, resource_name: str) -> None:
        """
        Initialize resource store.

        Args:
            session_id: Session identifier
            resource_name: Resource collection name
        """
        self._session_id = session_id
        self._resource_name = resource_name
        self._session_dir = get_session_dir(session_id)
        self._data_file = self._session_dir / f"{resource_name}.json"
        self._schema_file = self._session_dir / ".schemas" / f"{resource_name}.json"
        self._meta_file = self._session_dir / ".schemas" / f"{resource_name}.meta.json"

    def _load_data(self) -> builtins.list[dict[str, Any]]:
        """Load data from JSON file."""
        if not self._data_file.exists():
            return []
        try:
            with open(self._data_file, encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, list):
                    return []
                return data
        except (json.JSONDecodeError, OSError):
            return []

    def _save_data(self, items: builtins.list[dict[str, Any]]) -> None:
        """Save data to JSON file."""
        try:
            with open(self._data_file, "w", encoding="utf-8") as f:
                json.dump(items, f, indent=2, ensure_ascii=False)
        except OSError as exc:
            raise RuntimeError(f"Failed to save data: {exc}") from exc

    def _load_meta(self) -> dict[str, Any]:
        """Load metadata (auto_id counter)."""
        if not self._meta_file.exists():
            return {"auto_id": 1}
        try:
            with open(self._meta_file, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {"auto_id": 1}

    def _save_meta(self, meta: dict[str, Any]) -> None:
        """Save metadata."""
        try:
            with open(self._meta_file, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2)
        except OSError:
            pass  # Non-critical

    def _load_schema(self) -> dict[str, Any] | None:
        """Load schema metadata if it exists."""
        if not self._schema_file.exists():
            return None
        try:
            with open(self._schema_file, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    def _update_schema(self, record: dict[str, Any]) -> None:
        """
        Extract and save schema from a record.

        Schema includes field names and an example record for format consistency.
        """
        schema = {
            "fields": sorted(record.keys()),
            "example": deepcopy(record),
            "updated_at": datetime.now().isoformat(),
        }
        try:
            with open(self._schema_file, "w", encoding="utf-8") as f:
                json.dump(schema, f, indent=2, ensure_ascii=False)
        except OSError:
            pass  # Non-critical

    def get_schema(self) -> dict[str, Any] | None:
        """
        Get learned schema for this resource.

        Returns:
            Schema dict with 'fields', 'example', and 'updated_at', or None if no schema exists
        """
        return self._load_schema()

    def _next_id(self, items: builtins.list[dict[str, Any]]) -> int:
        """Calculate next available ID."""
        meta = self._load_meta()
        auto_id = meta.get("auto_id", 1)

        # Find max existing ID
        existing_ids = [item.get("id") for item in items if isinstance(item.get("id"), int)]
        max_existing = max(existing_ids or [0])

        next_id = max(auto_id, max_existing + 1)
        meta["auto_id"] = next_id + 1
        self._save_meta(meta)

        return next_id

    def _find_index(self, items: builtins.list[dict[str, Any]], identifier: Any) -> int | None:
        """Find the index of a record by identifier."""
        target = _normalize_identifier(identifier)
        for index, record in enumerate(items):
            record_id = record.get("id")
            if _normalize_identifier(record_id) == target:
                return index
        return None

    def insert(self, obj: dict[str, Any]) -> dict[str, Any]:
        """
        Insert a new record.

        Args:
            obj: Record to insert (will be deep-copied)

        Returns:
            Inserted record with ID assigned

        Raises:
            ValueError: If record with ID already exists
        """
        items = self._load_data()
        record = deepcopy(obj)

        # Handle ID assignment
        if "id" in record and record["id"] is not None:
            existing_id = record["id"]
            normalized = _normalize_identifier(existing_id)
            if self._find_index(items, normalized) is not None:
                raise ValueError("Resource with identifier already exists")
            record["id"] = normalized
        else:
            record["id"] = self._next_id(items)

        items.append(record)
        self._save_data(items)
        self._update_schema(record)

        return deepcopy(record)

    def get(self, identifier: Any) -> dict[str, Any] | None:
        """
        Get a record by identifier.

        Args:
            identifier: Record ID

        Returns:
            Record dict if found, None otherwise
        """
        items = self._load_data()
        index = self._find_index(items, identifier)
        if index is None:
            return None
        return deepcopy(items[index])

    def delete(self, identifier: Any) -> bool:
        """
        Delete a record by identifier.

        Args:
            identifier: Record ID

        Returns:
            True if deleted, False if not found
        """
        items = self._load_data()
        index = self._find_index(items, identifier)
        if index is None:
            return False
        items.pop(index)
        self._save_data(items)
        return True

    def replace(self, identifier: Any, obj: dict[str, Any]) -> dict[str, Any] | None:
        """
        Replace an entire record.

        Args:
            identifier: Record ID
            obj: New record data (ID will be preserved)

        Returns:
            Updated record if found, None otherwise
        """
        items = self._load_data()
        index = self._find_index(items, identifier)
        if index is None:
            return None

        existing = items[index]
        record = deepcopy(obj)
        record["id"] = existing.get("id")
        items[index] = record
        self._save_data(items)
        self._update_schema(record)

        return deepcopy(record)

    def update(self, identifier: Any, changes: dict[str, Any]) -> dict[str, Any] | None:
        """
        Partially update a record.

        Args:
            identifier: Record ID
            changes: Fields to update (cannot change ID)

        Returns:
            Updated record if found, None otherwise
        """
        items = self._load_data()
        index = self._find_index(items, identifier)
        if index is None:
            return None

        existing = deepcopy(items[index])
        for key, value in changes.items():
            if key == "id":
                continue
            existing[key] = value
        items[index] = existing
        self._save_data(items)
        self._update_schema(existing)

        return deepcopy(existing)

    def list(
        self,
        *,
        limit: int | None = None,
        offset: int = 0,
        sort: str | None = None,
    ) -> tuple[builtins.list[dict[str, Any]], int]:
        """
        List all records with optional pagination and sorting.

        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            sort: Field name to sort by (prefix with "-" for descending)

        Returns:
            Tuple of (items, total_count)
        """
        items = self._load_data()
        total = len(items)

        # Sort if requested
        if sort:
            reverse = sort.startswith("-")
            field = sort[1:] if reverse else sort
            items.sort(key=lambda item: item.get(field, ""), reverse=reverse)

        # Apply pagination
        if offset > 0:
            items = items[offset:]
        if limit is not None and limit >= 0:
            items = items[:limit]

        return [deepcopy(item) for item in items], total

    def search(self, criteria: dict[str, Any]) -> Iterable[dict[str, Any]]:
        """
        Search records matching criteria.

        Args:
            criteria: Dict of field->value pairs to match
                     Supports __contains, __icontains, __startswith, __endswith suffixes

        Returns:
            Iterable of matching records
        """
        items = self._load_data()
        results = [deepcopy(item) for item in items]

        for key, raw_value in criteria.items():
            if raw_value is None:
                continue

            value = raw_value
            if isinstance(value, list):
                value = value[-1] if value else None
                if value is None:
                    continue

            # Skip pagination/sort params
            if key in {"limit", "offset", "sort"}:
                continue

            # Apply filters
            if key.endswith("__contains"):
                field = key[:-10]
                value_str = str(value)
                results = [item for item in results if value_str in str(item.get(field, ""))]
            elif key.endswith("__icontains"):
                field = key[:-11]
                value_str = str(value).lower()
                results = [
                    item for item in results if value_str in str(item.get(field, "")).lower()
                ]
            elif key.endswith("__startswith"):
                field = key[:-12]
                value_str = str(value)
                results = [
                    item for item in results if str(item.get(field, "")).startswith(value_str)
                ]
            elif key.endswith("__endswith"):
                field = key[:-10]
                value_str = str(value)
                results = [item for item in results if str(item.get(field, "")).endswith(value_str)]
            else:
                results = [item for item in results if item.get(key) == value]

        return results
