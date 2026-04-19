# Architecture

## Overview

`HealthMCP` exposes Apache incubator health report data from Markdown files in `tools/health/reports` through a small MCP-compatible interface.

The project follows the same broad shape as `PodlingsMCP`:

- `server.py`
  A tiny top-level entrypoint for MCP clients.
- `src/apache_health_mcp/protocol.py`
  The JSON-RPC/MCP protocol loop over stdio.
- `src/apache_health_mcp/tools.py`
  Dependency-light tool handlers that wrap the parser/query logic.
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
- `get_report_summary`
- `get_report_markdown`
- `query_metric_rankings`

It also resolves the reports directory from either:

- the explicit `reports_dir` tool argument
- the `--reports-dir` startup argument
- the default `reports`

### `src/apache_health_mcp/protocol.py`

This module implements the stdio MCP/JSON-RPC behavior. It supports:

- `initialize`
- `tools/list`
- `tools/call`

The implementation delegates actual report operations to `tools.py`.

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
