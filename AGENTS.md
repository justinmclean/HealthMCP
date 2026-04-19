# AGENTS

## Purpose

This repository contains a small dependency-light MCP server for working with Apache Incubator health report Markdown files from `tools/health/reports`.

## Project Layout

- `src/apache_health_mcp/parser.py`
  - Markdown report loading, parsing, normalization, and query helpers
- `src/apache_health_mcp/tools.py`
  - Tool handlers and shared reports-directory resolution
- `src/apache_health_mcp/protocol.py`
  - JSON-RPC/MCP stdio protocol handling
- `server.py`
  - Thin entrypoint
- `tests/`
  - Unit and integration tests
- `tests/test_parser.py`
  - Parser, tools, and protocol helper coverage
- `tests/test_mcp_integration.py`
  - End-to-end MCP stdio coverage
- `docs/architecture.md`
  - High-level module and runtime structure

## Key Defaults And Concepts

- `--reports-dir` controls the default reports directory in MCP client config.
- If not set, the server defaults to `reports`.
- Report parsing is centered on the `## Window Details` section.
- Supported windows include `3m`, `6m`, `12m`, and `to-date`.
- The server queries pre-generated report files; it does not run Apache’s upstream health data collection script.

## Developer Workflow

Use these commands before finishing changes:

- `make check-format`
- `make lint`
- `make typecheck`
- `make test`

Coverage is available via:

- `make coverage`

## Contribution Guidelines

- Keep report parsing logic in `src/apache_health_mcp/parser.py`.
- Keep user-facing tool handlers in `src/apache_health_mcp/tools.py`.
- Keep MCP/JSON-RPC protocol wiring in `src/apache_health_mcp/protocol.py`.
- Keep `server.py` minimal.
- Add tests for any new tool, query shape, or report parsing rule.
- Update `README.md` and `docs/architecture.md` when changing public tools or runtime structure.

## Testing Notes

- Parsing and helper behavior belongs in `tests/test_parser.py`.
- MCP stdio session coverage belongs in `tests/test_mcp_integration.py`.
