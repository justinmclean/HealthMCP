from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

from tests.fixtures import ALPHA_REPORT

ROOT = Path(__file__).resolve().parent.parent
SERVER_SCRIPT = ROOT / "server.py"


class McpProtocolTests(unittest.TestCase):
    def make_reports_dir(self) -> tempfile.TemporaryDirectory[str]:
        temp_dir = tempfile.TemporaryDirectory()
        path = Path(temp_dir.name)
        (path / "Alpha.md").write_text(ALPHA_REPORT, encoding="utf-8")
        return temp_dir

    def _run_session(self, messages: list[Any], reports_dir: str) -> list[Any]:
        lines = [json.dumps(message) for message in messages]
        return self._run_raw_session(lines, reports_dir)

    def _run_raw_session(self, lines: list[str], reports_dir: str) -> list[Any]:
        proc = subprocess.Popen(
            [sys.executable, str(SERVER_SCRIPT), "--reports-dir", reports_dir],
            cwd=str(ROOT),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            responses = []
            assert proc.stdin is not None
            assert proc.stdout is not None
            assert proc.stderr is not None

            for line in lines:
                proc.stdin.write(line + "\n")
                proc.stdin.flush()
                responses.append(json.loads(proc.stdout.readline()))

            proc.stdin.close()
            proc.terminate()
            proc.wait(timeout=5)
            proc.stdout.close()
            proc.stderr.close()
            return responses
        finally:
            if proc.stdout and not proc.stdout.closed:
                proc.stdout.close()
            if proc.stderr and not proc.stderr.closed:
                proc.stderr.close()
            if proc.poll() is None:
                proc.kill()

    def test_initialize_and_tools_list(self) -> None:
        with self.make_reports_dir() as reports_dir:
            responses = self._run_session(
                [
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {"protocolVersion": "2024-11-05"},
                    },
                    {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
                ],
                reports_dir,
            )

        self.assertEqual(responses[0]["result"]["serverInfo"]["name"], "apache-health-mcp")
        tool_names = [tool["name"] for tool in responses[1]["result"]["tools"]]
        self.assertEqual(
            tool_names,
            [
                "health_overview",
                "list_podlings",
                "search_podlings",
                "get_report_summary",
                "get_report_markdown",
                "get_window_metrics",
                "compare_windows",
                "query_metric_rankings",
                "list_metrics",
            ],
        )

    def test_tools_call_success(self) -> None:
        with self.make_reports_dir() as reports_dir:
            responses = self._run_session(
                [
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {"protocolVersion": "2024-11-05"},
                    },
                    {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {
                            "name": "get_report_summary",
                            "arguments": {"podling": "Alpha"},
                        },
                    },
                ],
                reports_dir,
            )

        self.assertEqual(responses[1]["result"]["structuredContent"]["podling"], "Alpha")
        self.assertEqual(
            responses[1]["result"]["structuredContent"]["latest_metrics"]["3m"]["commits"], 42
        )

    def test_tools_call_search_success(self) -> None:
        with self.make_reports_dir() as reports_dir:
            responses = self._run_session(
                [
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {"protocolVersion": "2024-11-05"},
                    },
                    {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {
                            "name": "search_podlings",
                            "arguments": {"query": "alp"},
                        },
                    },
                ],
                reports_dir,
            )

        self.assertEqual(responses[1]["result"]["structuredContent"]["results"], ["Alpha"])

    def test_tools_call_compare_windows_success(self) -> None:
        with self.make_reports_dir() as reports_dir:
            responses = self._run_session(
                [
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {"protocolVersion": "2024-11-05"},
                    },
                    {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {
                            "name": "compare_windows",
                            "arguments": {"podling": "Alpha", "windows": ["3m", "6m"]},
                        },
                    },
                ],
                reports_dir,
            )

        payload = responses[1]["result"]["structuredContent"]
        self.assertEqual(payload["windows"]["3m"]["commits"], 42)
        self.assertEqual(payload["windows"]["6m"]["commits"], 70)
        self.assertEqual(payload["windows"]["3m"]["trends"]["commits"], "up")
        self.assertEqual(payload["windows"]["6m"]["trends"]["median_gap_days"], "flat")

    def test_tools_call_unknown_tool_returns_jsonrpc_error(self) -> None:
        with self.make_reports_dir() as reports_dir:
            responses = self._run_session(
                [
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {"protocolVersion": "2024-11-05"},
                    },
                    {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {"name": "missing_tool", "arguments": {}},
                    },
                ],
                reports_dir,
            )

        self.assertEqual(responses[1]["error"]["code"], -32602)
        self.assertIn("Unknown tool", responses[1]["error"]["message"])

    def test_tools_call_invalid_arguments_returns_jsonrpc_error(self) -> None:
        with self.make_reports_dir() as reports_dir:
            responses = self._run_session(
                [
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {"protocolVersion": "2024-11-05"},
                    },
                    {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {"name": "get_report_summary", "arguments": []},
                    },
                ],
                reports_dir,
            )

        self.assertEqual(responses[1]["error"]["code"], -32602)
        self.assertIn("Tool arguments must be an object", responses[1]["error"]["message"])

    def test_tools_call_handler_error_returns_mcp_error_payload(self) -> None:
        with self.make_reports_dir() as reports_dir:
            responses = self._run_session(
                [
                    {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {"protocolVersion": "2024-11-05"},
                    },
                    {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {
                            "name": "get_report_summary",
                            "arguments": {"podling": "MissingPodling"},
                        },
                    },
                ],
                reports_dir,
            )

        self.assertTrue(responses[1]["result"]["isError"])
        payload = responses[1]["result"]["structuredContent"]
        self.assertFalse(payload["ok"])
        self.assertIn("MissingPodling", payload["error"])

    def test_unknown_method_returns_jsonrpc_error(self) -> None:
        with self.make_reports_dir() as reports_dir:
            responses = self._run_session(
                [
                    {"jsonrpc": "2.0", "id": 1, "method": "unknown/method", "params": {}},
                ],
                reports_dir,
            )

        self.assertEqual(responses[0]["error"]["code"], -32601)
        self.assertIn("Method 'unknown/method' not found", responses[0]["error"]["message"])

    def test_batch_request_returns_batch_response(self) -> None:
        with self.make_reports_dir() as reports_dir:
            responses = self._run_session(
                [
                    [
                        {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
                        {
                            "jsonrpc": "2.0",
                            "method": "notifications/initialized",
                            "params": {},
                        },
                        {
                            "jsonrpc": "2.0",
                            "id": 2,
                            "method": "tools/call",
                            "params": {
                                "name": "get_report_summary",
                                "arguments": {"podling": "Alpha"},
                            },
                        },
                        {"jsonrpc": "2.0", "id": 3, "method": "missing/method", "params": {}},
                    ]
                ],
                reports_dir,
            )

        batch = responses[0]
        self.assertIsInstance(batch, list)
        self.assertEqual([item["id"] for item in batch], [1, 2, 3])
        self.assertIn("tools", batch[0]["result"])
        self.assertEqual(batch[1]["result"]["structuredContent"]["podling"], "Alpha")
        self.assertEqual(batch[2]["error"]["code"], -32601)

    def test_malformed_json_returns_structured_parse_error(self) -> None:
        with self.make_reports_dir() as reports_dir:
            responses = self._run_raw_session(['{"broken"'], reports_dir)

        self.assertEqual(responses[0]["jsonrpc"], "2.0")
        self.assertEqual(responses[0]["id"], None)
        self.assertEqual(responses[0]["error"]["code"], -32700)
        self.assertEqual(responses[0]["error"]["data"]["type"], "parse_error")

    def test_malformed_request_shape_returns_structured_error(self) -> None:
        with self.make_reports_dir() as reports_dir:
            responses = self._run_session(
                [
                    ["not a request object"],
                    {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": []},
                ],
                reports_dir,
            )

        self.assertEqual(responses[0][0]["id"], None)
        self.assertEqual(responses[0][0]["error"]["code"], -32600)
        self.assertEqual(responses[0][0]["error"]["data"]["type"], "invalid_request")
        self.assertEqual(responses[1]["error"]["code"], -32602)
        self.assertEqual(responses[1]["error"]["data"]["field"], "params")
