from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from apache_health_mcp import protocol, tools
from tests.fixtures import make_reports_dir


class ProtocolTests(unittest.TestCase):
    def make_reports_dir(self):
        return make_reports_dir()

    def test_jsonrpc_result_helper(self) -> None:
        response = protocol.jsonrpc_result(7, {"ok": True})

        self.assertEqual(response, {"jsonrpc": "2.0", "id": 7, "result": {"ok": True}})

    def test_jsonrpc_error_helper(self) -> None:
        response = protocol.jsonrpc_error(8, -1, "bad")

        self.assertEqual(
            response,
            {"jsonrpc": "2.0", "id": 8, "error": {"code": -1, "message": "bad"}},
        )

    def test_tool_response_helper(self) -> None:
        response = protocol.tool_response({"message": "hello"}, is_error=True)

        self.assertTrue(response["isError"])
        self.assertEqual(response["structuredContent"], {"message": "hello"})
        self.assertEqual(json.loads(response["content"][0]["text"]), {"message": "hello"})

    def test_list_tools_payload_contains_expected_tools(self) -> None:
        tool_names = [tool["name"] for tool in protocol.list_tools_payload()]

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

    def test_handle_message_initialize(self) -> None:
        response = protocol.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2024-11-05"},
            }
        )

        self.assertEqual(response["result"]["serverInfo"]["name"], "apache-health-mcp")

    def test_handle_message_initialize_uses_default_protocol_version(self) -> None:
        response = protocol.handle_message(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        )

        self.assertEqual(response["result"]["protocolVersion"], "2024-11-05")

    def test_handle_message_tools_list(self) -> None:
        response = protocol.handle_message(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        )

        self.assertEqual(len(response["result"]["tools"]), 9)

    def test_call_tool_success(self) -> None:
        with self.make_reports_dir() as reports_dir:
            result = protocol.call_tool("health_overview", {"reports_dir": reports_dir})

        self.assertNotIn("isError", result)
        self.assertEqual(result["structuredContent"]["report_count"], 2)

    def test_call_tool_error_payload(self) -> None:
        result = protocol.call_tool("get_report_summary", {"podling": "Missing"})

        self.assertTrue(result["isError"])
        payload = result["structuredContent"]
        self.assertFalse(payload["ok"])

    def test_call_tool_unknown_tool_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            protocol.call_tool("missing_tool", {})

    def test_handle_message_invalid_tool_arguments(self) -> None:
        response = protocol.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "health_overview", "arguments": []},
            }
        )

        self.assertEqual(response["error"]["code"], -32602)

    def test_handle_message_rejects_non_object_request(self) -> None:
        response = protocol.handle_message(["not", "an", "object"])

        self.assertEqual(response["id"], None)
        self.assertEqual(response["error"]["code"], -32600)
        self.assertEqual(response["error"]["data"]["type"], "invalid_request")

    def test_handle_message_rejects_missing_jsonrpc_version(self) -> None:
        response = protocol.handle_message({"id": 1, "method": "tools/list", "params": {}})

        self.assertEqual(response["id"], 1)
        self.assertEqual(response["error"]["code"], -32600)
        self.assertEqual(response["error"]["data"]["field"], "jsonrpc")

    def test_handle_message_rejects_invalid_id_type(self) -> None:
        response = protocol.handle_message(
            {"jsonrpc": "2.0", "id": True, "method": "tools/list", "params": {}}
        )

        self.assertEqual(response["id"], None)
        self.assertEqual(response["error"]["code"], -32600)
        self.assertEqual(response["error"]["data"]["field"], "id")

    def test_handle_message_rejects_missing_method(self) -> None:
        response = protocol.handle_message({"jsonrpc": "2.0", "id": 1, "params": {}})

        self.assertEqual(response["error"]["code"], -32600)
        self.assertEqual(response["error"]["data"]["field"], "method")

    def test_handle_message_rejects_non_object_params(self) -> None:
        response = protocol.handle_message(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": []}
        )

        self.assertEqual(response["error"]["code"], -32602)
        self.assertEqual(response["error"]["data"]["field"], "params")

    def test_handle_message_rejects_unknown_tool_argument(self) -> None:
        response = protocol.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "list_metrics",
                    "arguments": {"unexpected": "value"},
                },
            }
        )

        self.assertEqual(response["error"]["code"], -32602)
        self.assertIn("Unknown tool argument", response["error"]["message"])

    def test_handle_message_unknown_method(self) -> None:
        response = protocol.handle_message(
            {"jsonrpc": "2.0", "id": 1, "method": "unknown/method", "params": {}}
        )

        self.assertEqual(response["error"]["code"], -32601)

    def test_handle_notification_returns_no_response(self) -> None:
        response = protocol.handle_message(
            {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}
        )

        self.assertEqual(response, {})

    def test_handle_payload_processes_batch_requests(self) -> None:
        response = protocol.handle_payload(
            [
                {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
                {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
                {"jsonrpc": "2.0", "id": 2, "method": "unknown/method", "params": {}},
                "bad request",
            ]
        )

        self.assertIsInstance(response, list)
        assert isinstance(response, list)
        self.assertEqual([item["id"] for item in response], [1, 2, None])
        self.assertIn("tools", response[0]["result"])
        self.assertEqual(response[1]["error"]["code"], -32601)
        self.assertEqual(response[2]["error"]["code"], -32600)

    def test_handle_payload_rejects_empty_batch(self) -> None:
        response = protocol.handle_payload([])

        self.assertIsInstance(response, dict)
        assert isinstance(response, dict)
        self.assertEqual(response["id"], None)
        self.assertEqual(response["error"]["code"], -32600)

    def test_main_processes_parse_error_and_valid_message(self) -> None:
        stdin = mock.Mock()
        stdin.__iter__ = mock.Mock(
            return_value=iter(
                [
                    "\n",
                    '{"broken"\n',
                    '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}\n',
                ]
            )
        )
        stdout = mock.Mock()
        writes: list[str] = []
        stdout.write.side_effect = writes.append

        with mock.patch.object(protocol.sys, "stdin", stdin):
            with mock.patch.object(protocol.sys, "stdout", stdout):
                exit_code = protocol.main([])

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(writes), 2)
        first = json.loads(writes[0])
        second = json.loads(writes[1])
        self.assertEqual(first["error"]["code"], -32700)
        self.assertEqual(first["id"], None)
        self.assertIn("tools", second["result"])

    def test_main_processes_batch_message(self) -> None:
        stdin = mock.Mock()
        stdin.__iter__ = mock.Mock(
            return_value=iter(
                [
                    json.dumps(
                        [
                            {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
                            {
                                "jsonrpc": "2.0",
                                "method": "notifications/initialized",
                                "params": {},
                            },
                            {"jsonrpc": "2.0", "id": 2, "method": "unknown/method", "params": {}},
                        ]
                    )
                    + "\n",
                ]
            )
        )
        stdout = mock.Mock()
        writes: list[str] = []
        stdout.write.side_effect = writes.append

        with mock.patch.object(protocol.sys, "stdin", stdin):
            with mock.patch.object(protocol.sys, "stdout", stdout):
                exit_code = protocol.main([])

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(writes), 1)
        batch_response = json.loads(writes[0])
        self.assertEqual([item["id"] for item in batch_response], [1, 2])
        self.assertIn("tools", batch_response[0]["result"])
        self.assertEqual(batch_response[1]["error"]["code"], -32601)

    def test_main_uses_default_reports_dir_when_missing(self) -> None:
        stdin = mock.Mock()
        stdin.__iter__ = mock.Mock(return_value=iter([]))
        stdout = mock.Mock()

        tools._CONFIGURED_REPORTS_DIR = None
        with mock.patch.object(protocol.sys, "stdin", stdin):
            with mock.patch.object(protocol.sys, "stdout", stdout):
                exit_code = protocol.main([])

        self.assertEqual(exit_code, 0)
        self.assertEqual(tools.resolve_reports_dir(None), "reports")

    def test_main_accepts_reports_dir_argument(self) -> None:
        stdin = mock.Mock()
        stdin.__iter__ = mock.Mock(return_value=iter([]))
        stdout = mock.Mock()

        tools._CONFIGURED_REPORTS_DIR = None
        with mock.patch.object(protocol.sys, "stdin", stdin):
            with mock.patch.object(protocol.sys, "stdout", stdout):
                exit_code = protocol.main(["--reports-dir", "/tmp/reports"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(tools.resolve_reports_dir(None), "/tmp/reports")
