from __future__ import annotations

from typing import Any

from apache_health_mcp import schemas
from apache_health_mcp.parser import (
    find_report,
    query_metric,
    reports_overview,
    summarize_report,
)

DEFAULT_REPORTS_DIR = "reports"
_CONFIGURED_REPORTS_DIR: str | None = None
VALID_WINDOWS = {"3m", "6m", "12m", "to-date"}
VALID_METRICS = {
    "releases",
    "median_gap_days",
    "new_contributors",
    "unique_committers",
    "commits",
    "issues_opened",
    "issues_closed",
    "prs_opened",
    "prs_merged",
    "median_merge_days",
    "median_reviewers_per_pr",
    "reviewer_div_eff",
    "pr_author_div_eff",
    "unique_reviewers",
    "unique_authors",
    "bus50",
    "bus75",
    "reports_count",
    "avg_mentor_signoffs",
    "dev_messages",
    "dev_unique_posters",
}


def configure_reports_dir(value: str | None) -> None:
    global _CONFIGURED_REPORTS_DIR
    if value:
        _CONFIGURED_REPORTS_DIR = value


def resolve_reports_dir(value: str | None) -> str:
    if value is None:
        return _CONFIGURED_REPORTS_DIR or DEFAULT_REPORTS_DIR
    if not isinstance(value, str):
        raise ValueError("'reports_dir' must be a string")
    stripped = value.strip()
    if not stripped:
        raise ValueError("'reports_dir' must be a non-empty string")
    return stripped


def require_non_empty_string(value: Any, key: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"'{key}' must be a string")
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"'{key}' must be a non-empty string")
    return stripped


def optional_number(value: Any, key: str) -> float | None:
    if value is None:
        return None
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"'{key}' must be a number")
    return float(value)


def require_window(value: Any) -> str:
    window = require_non_empty_string(value, "window")
    if window not in VALID_WINDOWS:
        choices = ", ".join(sorted(VALID_WINDOWS))
        raise ValueError(f"'window' must be one of: {choices}")
    return window


def require_windows(value: Any) -> list[str]:
    if not isinstance(value, list):
        raise ValueError("'windows' must be a list of window names")
    if len(value) not in {2, 3}:
        raise ValueError("'windows' must contain exactly 2 or 3 window names")

    resolved: list[str] = []
    for item in value:
        window = require_window(item)
        if window in resolved:
            raise ValueError("'windows' must not contain duplicates")
        resolved.append(window)
    return resolved


def require_metric(value: Any) -> str:
    metric = require_non_empty_string(value, "metric")
    if metric not in VALID_METRICS:
        choices = ", ".join(sorted(VALID_METRICS))
        raise ValueError(f"'metric' must be one of: {choices}")
    return metric


def require_limit(value: Any) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("'limit' must be an integer")
    if value <= 0:
        raise ValueError("'limit' must be greater than 0")
    return value


def require_sort_desc(value: Any) -> bool:
    if not isinstance(value, bool):
        raise ValueError("'sort_desc' must be a boolean")
    return value


def health_overview(reports_dir: str | None = None) -> dict[str, Any]:
    """Return a high-level summary of the available Apache health reports."""
    return reports_overview(resolve_reports_dir(reports_dir))


def list_podlings(reports_dir: str | None = None) -> dict[str, Any]:
    """List podlings that have a parsed markdown report."""
    overview = reports_overview(resolve_reports_dir(reports_dir))
    return {
        "reports_dir": overview["reports_dir"],
        "report_count": overview["report_count"],
        "podlings": overview["podlings"],
    }


def search_podlings(
    query: str,
    reports_dir: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Search podling names by case-insensitive substring."""
    resolved_query = require_non_empty_string(query, "query").casefold()
    resolved_limit = require_limit(limit)
    overview = reports_overview(resolve_reports_dir(reports_dir))
    matches = [name for name in overview["podlings"] if resolved_query in name.casefold()]
    return {
        "query": query,
        "count": len(matches),
        "results": matches[:resolved_limit],
    }


def get_report_summary(podling: str, reports_dir: str | None = None) -> dict[str, Any]:
    """Get parsed metrics for one podling report."""
    resolved_podling = require_non_empty_string(podling, "podling")
    return summarize_report(find_report(resolve_reports_dir(reports_dir), resolved_podling))


def get_report_markdown(podling: str, reports_dir: str | None = None) -> str:
    """Return the raw markdown for one podling report."""
    resolved_podling = require_non_empty_string(podling, "podling")
    report = find_report(resolve_reports_dir(reports_dir), resolved_podling)
    return report.raw_text


def get_window_metrics(
    podling: str,
    window: str,
    reports_dir: str | None = None,
) -> dict[str, Any]:
    """Return metrics for a single podling/window combination."""
    resolved_podling = require_non_empty_string(podling, "podling")
    resolved_window = require_window(window)
    report = find_report(resolve_reports_dir(reports_dir), resolved_podling)
    for metrics in report.windows:
        if metrics.window == resolved_window:
            return {
                "podling": report.podling,
                "generated_on": report.generated_on,
                "window": resolved_window,
                "metrics": metrics.to_dict(),
            }
    raise ValueError(f"Window '{resolved_window}' not available for podling '{resolved_podling}'")


def compare_windows(
    podling: str,
    windows: list[str],
    reports_dir: str | None = None,
) -> dict[str, Any]:
    """Compare one podling across two or three windows."""
    resolved_podling = require_non_empty_string(podling, "podling")
    resolved_windows = require_windows(windows)
    report = find_report(resolve_reports_dir(reports_dir), resolved_podling)

    by_window = {metrics.window: metrics.to_dict() for metrics in report.windows}
    missing = [window for window in resolved_windows if window not in by_window]
    if missing:
        raise ValueError(
            f"Window(s) not available for podling '{resolved_podling}': {', '.join(missing)}"
        )

    return {
        "podling": report.podling,
        "generated_on": report.generated_on,
        "windows": {window: by_window[window] for window in resolved_windows},
    }


def query_metric_rankings(
    metric: str,
    window: str = "3m",
    min_value: float | None = None,
    max_value: float | None = None,
    sort_desc: bool = True,
    limit: int = 20,
    reports_dir: str | None = None,
) -> dict[str, Any]:
    """Rank podlings by one parsed metric for a specific window."""
    resolved_metric = require_metric(metric)
    resolved_window = require_window(window)
    resolved_limit = require_limit(limit)
    resolved_sort_desc = require_sort_desc(sort_desc)
    resolved_min = optional_number(min_value, "min_value")
    resolved_max = optional_number(max_value, "max_value")
    if resolved_min is not None and resolved_max is not None and resolved_min > resolved_max:
        raise ValueError("'min_value' must be less than or equal to 'max_value'")

    rows = query_metric(
        reports_dir=resolve_reports_dir(reports_dir),
        metric=resolved_metric,
        window=resolved_window,
        min_value=resolved_min,
        max_value=resolved_max,
        sort_desc=resolved_sort_desc,
    )
    return {
        "metric": resolved_metric,
        "window": resolved_window,
        "count": len(rows),
        "results": rows[:resolved_limit],
    }


def list_metrics() -> dict[str, Any]:
    """Return the supported metrics and windows for querying."""
    return {
        "windows": sorted(VALID_WINDOWS),
        "metrics": sorted(VALID_METRICS),
    }


TOOLS: dict[str, dict[str, Any]] = {
    "health_overview": schemas.tool_definition(
        description="Return a high-level summary of the available Apache health reports.",
        handler=health_overview,
        properties=schemas.base_properties(),
    ),
    "list_podlings": schemas.tool_definition(
        description="List podlings that have a parsed markdown report.",
        handler=list_podlings,
        properties=schemas.base_properties(),
    ),
    "search_podlings": schemas.tool_definition(
        description="Search podling names by case-insensitive substring.",
        handler=search_podlings,
        properties=schemas.search_properties(),
        required=["query"],
    ),
    "get_report_summary": schemas.tool_definition(
        description="Get parsed metrics for one podling report.",
        handler=get_report_summary,
        properties=schemas.podling_properties(),
        required=["podling"],
    ),
    "get_report_markdown": schemas.tool_definition(
        description="Return the raw markdown for one podling report.",
        handler=get_report_markdown,
        properties=schemas.podling_properties(),
        required=["podling"],
    ),
    "get_window_metrics": schemas.tool_definition(
        description="Return metrics for a single podling/window combination.",
        handler=get_window_metrics,
        properties=schemas.window_metrics_properties(sorted(VALID_WINDOWS)),
        required=["podling", "window"],
    ),
    "compare_windows": schemas.tool_definition(
        description="Compare one podling across two or three windows.",
        handler=compare_windows,
        properties=schemas.compare_windows_properties(sorted(VALID_WINDOWS)),
        required=["podling", "windows"],
    ),
    "query_metric_rankings": schemas.tool_definition(
        description="Rank podlings by one parsed metric for a specific window.",
        handler=query_metric_rankings,
        properties=schemas.ranking_properties(sorted(VALID_METRICS), sorted(VALID_WINDOWS)),
        required=["metric"],
    ),
    "list_metrics": schemas.tool_definition(
        description="Return the supported metrics and windows for querying.",
        handler=list_metrics,
        properties={},
    ),
}
