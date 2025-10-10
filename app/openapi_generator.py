"""Dynamic OpenAPI/Swagger spec generation from learned schemas."""

from __future__ import annotations

import json
from typing import Any

from sandbox_runtime.filesystem import get_session_dir


def _infer_type(value: Any) -> str:
    """Infer OpenAPI type from a Python value."""
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "string"  # default fallback


def _schema_from_example(example: dict[str, Any]) -> dict[str, Any]:
    """Generate OpenAPI schema from an example record."""
    properties = {}
    for key, value in example.items():
        prop_type = _infer_type(value)
        properties[key] = {"type": prop_type}

        if isinstance(value, list) and value:
            # Infer array item type from first element
            item_type = _infer_type(value[0])
            properties[key]["items"] = {"type": item_type}
        elif isinstance(value, dict):
            # For nested objects, just mark as object
            properties[key] = {"type": "object"}

    return {
        "type": "object",
        "properties": properties,
        "example": example,
    }


def _generate_resource_paths(resource: str, schema_name: str, updated_at: str) -> dict[str, Any]:
    """Generate OpenAPI paths for a discovered resource."""

    resource_url = f"/{resource}"
    resource_id_url = f"/{resource}/{{id}}"
    resource_search_url = f"/{resource}/search"

    return {
        resource_url: {
            "get": {
                "summary": f"List {resource}",
                "description": f"Returns paginated list. Format learned from your first POST. Last updated: {updated_at}",
                "tags": [resource],
                "parameters": [
                    {"name": "limit", "in": "query", "schema": {"type": "integer"}},
                    {"name": "offset", "in": "query", "schema": {"type": "integer"}},
                    {"name": "sort", "in": "query", "schema": {"type": "string"}},
                ],
                "responses": {
                    "200": {
                        "description": "Paginated response (probably)",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "items": {
                                            "type": "array",
                                            "items": {
                                                "$ref": f"#/components/schemas/{schema_name}"
                                            },
                                        },
                                        "page": {
                                            "type": "object",
                                            "properties": {
                                                "total": {"type": "integer"},
                                                "limit": {"type": "integer"},
                                                "offset": {"type": "integer"},
                                            },
                                        },
                                    },
                                }
                            }
                        },
                    }
                },
            },
            "post": {
                "summary": f"Create {resource.removesuffix('s')}",
                "description": "This endpoint exists because you created it. The LLM remembers the format.",
                "tags": [resource],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": f"#/components/schemas/{schema_name}"}
                        }
                    },
                },
                "responses": {
                    "201": {
                        "description": "Created (with auto-generated ID)",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": f"#/components/schemas/{schema_name}"}
                            }
                        },
                    }
                },
            },
        },
        resource_id_url: {
            "get": {
                "summary": f"Get {resource.removesuffix('s')} by ID",
                "description": "Returns the record or 404. You know the drill.",
                "tags": [resource],
                "parameters": [
                    {
                        "name": "id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "integer"},
                        "description": "Record ID (auto-generated on POST)",
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Found it",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": f"#/components/schemas/{schema_name}"}
                            }
                        },
                    },
                    "404": {"description": "Not found (LLM couldn't find it either)"},
                },
            },
            "put": {
                "summary": f"Replace {resource.removesuffix('s')}",
                "description": "Full replacement. ID is preserved.",
                "tags": [resource],
                "parameters": [
                    {"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}
                ],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": f"#/components/schemas/{schema_name}"}
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "Replaced",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": f"#/components/schemas/{schema_name}"}
                            }
                        },
                    },
                    "404": {"description": "Not found"},
                },
            },
            "patch": {
                "summary": f"Update {resource.removesuffix('s')}",
                "description": "Partial update. Send only the fields you want to change.",
                "tags": [resource],
                "parameters": [
                    {"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}
                ],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"type": "object", "additionalProperties": True}
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "Updated",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": f"#/components/schemas/{schema_name}"}
                            }
                        },
                    },
                    "404": {"description": "Not found"},
                },
            },
            "delete": {
                "summary": f"Delete {resource.removesuffix('s')}",
                "description": "Deletes the record. Gone. Poof.",
                "tags": [resource],
                "parameters": [
                    {"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}
                ],
                "responses": {
                    "204": {"description": "Deleted"},
                    "404": {"description": "Already gone"},
                },
            },
        },
        resource_search_url: {
            "get": {
                "summary": f"Search {resource}",
                "description": (
                    "Flexible search. Use /search, /find, /query, or /filter - they all work. "
                    "Wildcards supported: name=Hart* (prefix), email=*@example.com (suffix), name=*art* (contains). "
                    "Or try query params like ?getByFieldName=value. The LLM figures it out."
                ),
                "tags": [resource],
                "parameters": [
                    {
                        "name": "query",
                        "in": "query",
                        "schema": {"type": "string"},
                        "description": "Any field from your schema. Use wildcards with *.",
                        "example": "Hart*",
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Search results (direct array, not paginated)",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {"$ref": f"#/components/schemas/{schema_name}"},
                                }
                            }
                        },
                    }
                },
            }
        },
    }


def generate_openapi_spec(session_id: str) -> dict[str, Any]:
    """
    Generate OpenAPI 3.0 spec based on learned schemas in the session.

    Scans the session directory for .schemas/*.json files and generates
    paths and schemas for each discovered resource.

    Args:
        session_id: Session identifier

    Returns:
        Complete OpenAPI 3.0 specification
    """
    session_dir = get_session_dir(session_id)
    schemas_dir = session_dir / ".schemas"

    paths: dict[str, Any] = {}
    components_schemas: dict[str, Any] = {}
    discovered_resources: list[str] = []

    # Scan for learned schemas
    if schemas_dir.exists():
        for schema_file in schemas_dir.glob("*.json"):
            # Skip metadata files
            if schema_file.name.endswith(".meta.json"):
                continue

            resource_name = schema_file.stem
            discovered_resources.append(resource_name)

            try:
                with open(schema_file) as f:
                    schema_data = json.load(f)

                example = schema_data.get("example", {})
                updated_at = schema_data.get("updated_at", "unknown")

                # Generate schema
                schema_name = resource_name.capitalize()
                components_schemas[schema_name] = _schema_from_example(example)

                # Generate paths
                resource_paths = _generate_resource_paths(resource_name, schema_name, updated_at)
                paths.update(resource_paths)

            except (json.JSONDecodeError, OSError):
                continue  # Skip invalid schema files

    # Add catch-all documentation
    paths["/{resource}"] = {
        "get": {
            "summary": "Try literally anything",
            "description": (
                "This is the universal endpoint. Just make a request to any path. "
                "The LLM will interpret your intent and generate code to handle it. "
                f"You've discovered {len(discovered_resources)} resource(s) so far: {', '.join(discovered_resources) if discovered_resources else 'none yet'}. "
                "Go ahead, surprise us."
            ),
            "tags": ["meta"],
            "parameters": [
                {"name": "resource", "in": "path", "required": True, "schema": {"type": "string"}}
            ],
            "responses": {
                "200": {"description": "Success (probably)"},
                "201": {"description": "Created something"},
                "204": {"description": "Deleted something"},
                "400": {"description": "The LLM couldn't figure out what you wanted"},
                "404": {"description": "Not found"},
            },
        }
    }

    discovered_note = (
        f"**Discovered Resources**: {', '.join(discovered_resources)}\n\n"
        if discovered_resources
        else "**Discovered Resources**: None yet. Start POSTing!\n\n"
    )

    return {
        "openapi": "3.1.0",
        "info": {
            "title": "The Last REST Service™ — Your Session",
            "version": "∞.0.0",
            "description": (
                f"This API spec was generated based on what YOU actually did in your session.\n\n"
                f"{discovered_note}"
                "These are the endpoints you invented. The formats you defined. "
                "The LLM learned from your first POST and remembers.\n\n"
                "**Pro tip**: Any path works. These are just the ones we've seen you use. "
                "The catch-all `/{resource}` handles everything else.\n\n"
                "**Session ID**: `{session_id}`"
            ),
        },
        "servers": [{"url": "http://localhost:8000", "description": "Local development"}],
        "paths": paths,
        "components": {"schemas": components_schemas} if components_schemas else {},
        "tags": [
            {
                "name": "meta",
                "description": "Meta-endpoints (health, swagger, the catch-all)",
            }
        ]
        + [
            {"name": resource, "description": f"Operations on {resource}"}
            for resource in discovered_resources
        ],
    }
