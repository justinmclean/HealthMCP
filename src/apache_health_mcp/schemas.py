from __future__ import annotations

from typing import Any

REPORTS_DIR_PROPERTY = {
    "type": "string",
    "description": "Optional local path to apache-health report Markdown files",
}
PODLING_PROPERTY = {"type": "string", "description": "Podling name"}
QUERY_PROPERTY = {"type": "string", "description": "Case-insensitive podling name search text"}
LIMIT_PROPERTY = {"type": "integer", "description": "Optional maximum number of results to return"}
NUMBER_FILTER_PROPERTY = {"type": "number", "description": "Optional inclusive metric value filter"}
SORT_DESC_PROPERTY = {
    "type": "boolean",
    "description": "Whether to sort metric rankings descending",
}


def input_schema(
    properties: dict[str, Any], *, required: list[str] | None = None
) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": required or [],
        "additionalProperties": False,
    }


def tool_definition(
    *,
    description: str,
    handler: Any,
    properties: dict[str, Any],
    required: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "description": description,
        "inputSchema": input_schema(properties, required=required),
        "handler": handler,
    }


def base_properties() -> dict[str, Any]:
    return {"reports_dir": REPORTS_DIR_PROPERTY}


def podling_properties() -> dict[str, Any]:
    return {
        **base_properties(),
        "podling": PODLING_PROPERTY,
    }


def search_properties() -> dict[str, Any]:
    return {
        **base_properties(),
        "query": QUERY_PROPERTY,
        "limit": LIMIT_PROPERTY,
    }


def window_property(windows: list[str]) -> dict[str, Any]:
    return {
        "type": "string",
        "description": "Health-report window",
        "enum": windows,
    }


def metric_property(metrics: list[str]) -> dict[str, Any]:
    return {
        "type": "string",
        "description": "Parsed health metric name",
        "enum": metrics,
    }


def window_metrics_properties(windows: list[str]) -> dict[str, Any]:
    return {
        **podling_properties(),
        "window": window_property(windows),
    }


def compare_windows_properties(windows: list[str]) -> dict[str, Any]:
    return {
        **podling_properties(),
        "windows": {
            "type": "array",
            "description": "Two or three health-report windows to compare",
            "items": window_property(windows),
            "minItems": 2,
            "maxItems": 3,
            "uniqueItems": True,
        },
    }


def ranking_properties(metrics: list[str], windows: list[str]) -> dict[str, Any]:
    return {
        **base_properties(),
        "metric": metric_property(metrics),
        "window": window_property(windows),
        "min_value": NUMBER_FILTER_PROPERTY,
        "max_value": NUMBER_FILTER_PROPERTY,
        "sort_desc": SORT_DESC_PROPERTY,
        "limit": LIMIT_PROPERTY,
    }
