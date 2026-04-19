# Architecture

## Overview

`HealthMCP` exposes Apache incubator health report data from Markdown files in `tools/health/reports` through a small MCP-compatible interface.

The project follows the same broad shape as `PodlingsMCP`:

- `server.py`
  A tiny top-level entrypoint for MCP clients.
- `src/apache_health_mcp/protocol.py`
  The JSON-RPC/MCP protocol loop over stdio.
- `src/apache_health_mcp/tools.py`
  Dependency-light tool handlers, argument validation, and the `TOOLS` registry.
- `src/apache_health_mcp/schemas.py`
  Shared MCP input schema fragments and schema-builder helpers.
- `src/apache_health_mcp/parser.py`
  The report parsing and query layer.

## Modules

### `src/apache_health_mcp/parser.py`

This module is responsible for:

- loading Markdown reports from a directory
- ignoring non-report files like `SUMMARY.md`
- parsing `_Generated on ..._`
- parsing `## Window Details` blocks for windows like `3m`, `6m`, `12m`, and `to-date`
- extracting structured metrics for releases, contributors, issues, PRs, reviews, bus factor, reports, and mailing list activity
- providing higher-level query helpers like report lookup, overview generation, and metric ranking

### `src/apache_health_mcp/tools.py`

This module provides the user-facing tool handlers:

- `health_overview`
- `list_podlings`
- `search_podlings`
- `get_report_summary`
- `get_report_markdown`
- `get_window_metrics`
- `compare_windows`
- `query_metric_rankings`
- `list_metrics`

It also resolves the reports directory from either:

- the explicit `reports_dir` tool argument
- the `--reports-dir` startup argument
- the default `reports`

Tool handlers return native structured payloads where possible. `get_report_markdown` returns raw text because the markdown report is the payload itself.

### `src/apache_health_mcp/schemas.py`

This module contains shared MCP input schema fragments and schema builder helpers. New tool schema definitions should be added here rather than inline in `protocol.py`.

### `src/apache_health_mcp/protocol.py`

This module implements the stdio MCP/JSON-RPC behavior. It supports:

- `initialize`
- `tools/list`
- `tools/call`

Requests can be sent as single JSON-RPC objects or as JSON-RPC batches. Batch responses omit notification-only messages and preserve per-request success or error payloads for the remaining messages. The protocol layer validates the JSON-RPC envelope before dispatching, returning structured `error.data` details for parse errors, invalid requests, invalid params, and unknown methods.

The implementation delegates actual report operations to `tools.py` and wraps structured tool results with both MCP `structuredContent` and a JSON text fallback in `content`.

### `server.py`

This file is intentionally tiny. It just imports `main` from `apache_health_mcp.protocol` and exits with that return code.

## Testing

The test suite currently has two layers:

- `tests/test_parser.py`
  Unit tests for parsing, query helpers, tool handlers, protocol helpers, error handling, and startup argument resolution.
- `tests/test_mcp_integration.py`
  End-to-end tests that spawn `server.py` as a subprocess and exercise MCP-style JSON-RPC requests over stdio.

## Design Notes

- The parser is intentionally tolerant of incomplete reports and missing fields.
- The top-level `server.py` is intentionally minimal so the real behavior stays in testable package modules.
- `tools.py` is dependency-light on purpose, which makes unit testing straightforward.
