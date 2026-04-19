# Apache Health MCP

This repo contains a small MCP server for querying the Apache Incubator health reports from [`tools/health/reports`](https://github.com/apache/incubator/tree/master/tools/health/reports).

It parses the Markdown report format used by Apache's health tooling and exposes MCP tools for:

- listing available podling reports
- searching podling names
- getting a parsed summary for one podling
- returning the raw Markdown report
- returning metrics for one specific window
- comparing one podling across two or three windows
- listing supported metrics and windows
- ranking podlings by a metric within a window like `3m`, `6m`, or `12m`

## Expected input

Point the server at a local directory containing Markdown files like:

```text
reports/
  Amoro.md
  Iggy.md
  ...
```

The parser is designed around the current Apache report structure, especially the `## Window Details` section.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install .
```

For local development:

```bash
make install-dev
```

## Run

```bash
health-mcp --reports-dir /path/to/incubator/tools/health/reports
```

The server uses `stdio`, so it is intended to be launched by an MCP client.

For local development without installing first, you can still launch the stdio server directly:

```bash
python3 server.py
```

The package also keeps `apache-health-mcp` as a backwards-compatible command alias.

## Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` and add:

```json
{
  "mcpServers": {
    "apache-health": {
      "command": "health-mcp",
      "args": [
        "--reports-dir",
        "/path/to/incubator/tools/health/reports"
      ]
    }
  }
}
```

Then restart Claude Desktop. If you installed into a virtual environment that is not on your `PATH`, use the absolute path to that environment's `health-mcp` command.

## MCP tools

`health_overview`
Returns the reports directory, report count, podling list, and latest generated date.

`list_podlings`
Returns the podling names available in the reports directory.

`search_podlings`
Searches podling names by case-insensitive substring with an optional result limit.

`get_report_summary`
Returns parsed window metrics for a single podling.

`get_report_markdown`
Returns the raw Markdown for a single podling report.

`get_window_metrics`
Returns metrics for one podling and one window such as `3m`, `6m`, `12m`, or `to-date`, including normalized trend words like `up`, `down`, and `flat` under `trends`.

`compare_windows`
Returns side-by-side metrics for one podling across two or three windows, including normalized trend words under each window's `trends`.

`query_metric_rankings`
Ranks podlings by a parsed metric such as `commits`, `prs_merged`, `dev_messages`, `bus50`, or `median_merge_days`.

`list_metrics`
Returns the supported metric names and available windows for querying.

## Development

Common tasks are available through `make`:

```bash
make format
make lint
make typecheck
make test
make coverage
make check
```

## Notes

- This server queries already-generated report files. It does not run Apache's upstream collection script.
- The workspace here did not include a local `reports/` directory, so the server is built to accept any local clone or copied snapshot of Apache's reports directory.
