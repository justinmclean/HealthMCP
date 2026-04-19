from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Callable

from apache_health_mcp import tools

ToolFunc = Callable[..., str]

TOOLS: dict[str, dict[str, Any]] = {
    "health_overview": {
        "description": "Return a high-level summary of the available Apache health reports.",
        "handler": tools.health_overview,
    },
    "list_podlings": {
        "description": "List podlings that have a parsed markdown report.",
        "handler": tools.list_podlings,
    },
    "search_podlings": {
        "description": "Search podling names by case-insensitive substring.",
        "handler": tools.search_podlings,
    },
    "get_report_summary": {
        "description": "Get parsed metrics for one podling report.",
        "handler": tools.get_report_summary,
    },
    "get_report_markdown": {
        "description": "Return the raw markdown for one podling report.",
        "handler": tools.get_report_markdown,
    },
    "get_window_metrics": {
        "description": "Return metrics for a single podling/window combination.",
        "handler": tools.get_window_metrics,
    },
    "compare_windows": {
        "description": "Compare one podling across two or three windows.",
        "handler": tools.compare_windows,
    },
    "query_metric_rankings": {
        "description": "Rank podlings by one parsed metric for a specific window.",
        "handler": tools.query_metric_rankings,
    },
    "list_metrics": {
        "description": "Return the supported metrics and windows for querying.",
        "handler": tools.list_metrics,
    },
}


def jsonrpc_result(message_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": message_id, "result": result}


def jsonrpc_error(message_id: Any, code: int, message: str) -> dict[str, Any]:
    safe_id = (
        message_id if isinstance(message_id, (str, int)) and not isinstance(message_id, bool) else 0
    )
    return {"jsonrpc": "2.0", "id": safe_id, "error": {"code": code, "message": message}}


def tool_response(text: str, is_error: bool = False) -> dict[str, Any]:
    return {
        "content": [{"type": "text", "text": text}],
        "isError": is_error,
    }


def list_tools_payload() -> list[dict[str, Any]]:
    return [
        {
            "name": name,
            "description": meta["description"],
            "inputSchema": {"type": "object"},
        }
        for name, meta in TOOLS.items()
    ]


def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name not in TOOLS:
        raise ValueError(f"Unknown tool: {name}")
    handler: ToolFunc = TOOLS[name]["handler"]
    try:
        return tool_response(handler(**arguments))
    except Exception as exc:
        payload = {"ok": False, "error": str(exc), "tool": name}
        return tool_response(json.dumps(payload, indent=2, sort_keys=True), is_error=True)


def handle_message(message: dict[str, Any]) -> dict[str, Any]:
    message_id = message.get("id")
    method = message.get("method")
    params = message.get("params") or {}

    if message_id is None and isinstance(method, str) and method.startswith("notifications/"):
        return {}

    if method == "initialize":
        return jsonrpc_result(
            message_id,
            {
                "protocolVersion": params.get("protocolVersion", "2024-11-05"),
                "serverInfo": {"name": "apache-health-mcp", "version": "0.1.0"},
                "capabilities": {"tools": {}},
            },
        )

    if method == "tools/list":
        return jsonrpc_result(message_id, {"tools": list_tools_payload()})

    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments", {})
        if not isinstance(name, str):
            return jsonrpc_error(message_id, -32602, "Tool name must be a string")
        if not isinstance(arguments, dict):
            return jsonrpc_error(message_id, -32602, "Tool arguments must be an object")
        try:
            return jsonrpc_result(message_id, call_tool(name, arguments))
        except ValueError as exc:
            return jsonrpc_error(message_id, -32602, str(exc))

    return jsonrpc_error(message_id, -32601, f"Method '{method}' not found")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apache Health MCP server")
    parser.add_argument("--reports-dir", help="Path to apache-health report Markdown files")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    tools.configure_reports_dir(args.reports_dir)

    for line in sys.stdin:
        raw = line.strip()
        if not raw:
            continue
        try:
            message = json.loads(raw)
        except json.JSONDecodeError:
            response = jsonrpc_error(0, -32700, "Parse error")
        else:
            response = handle_message(message)
        if response:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()

    return 0
