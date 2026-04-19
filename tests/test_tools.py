from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from apache_health_mcp import tools
from tests.fixtures import make_reports_dir


class ToolTests(unittest.TestCase):
    def test_tools_search_podlings_returns_matches(self) -> None:
        with make_reports_dir() as reports_dir:
            data = tools.search_podlings("alp", reports_dir)

        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"], ["Alpha"])

    def test_tools_search_podlings_applies_limit(self) -> None:
        with make_reports_dir() as reports_dir:
            data = tools.search_podlings("a", reports_dir, limit=1)

        self.assertEqual(len(data["results"]), 1)

    def test_tools_health_overview_returns_json(self) -> None:
        with make_reports_dir() as reports_dir:
            data = tools.health_overview(reports_dir)

        self.assertEqual(data["report_count"], 2)
        self.assertEqual(data["podlings"], ["Alpha", "Bravo"])

    def test_tools_list_podlings_returns_json(self) -> None:
        with make_reports_dir() as reports_dir:
            data = tools.list_podlings(reports_dir)

        self.assertEqual(data["report_count"], 2)
        self.assertEqual(data["podlings"], ["Alpha", "Bravo"])

    def test_tools_get_report_summary_returns_json(self) -> None:
        with make_reports_dir() as reports_dir:
            data = tools.get_report_summary("Alpha", reports_dir)

        self.assertEqual(data["podling"], "Alpha")
        self.assertEqual(data["latest_metrics"]["3m"]["dev_messages"], 25)

    def test_tools_get_report_markdown_returns_raw_text(self) -> None:
        with make_reports_dir() as reports_dir:
            markdown = tools.get_report_markdown("Bravo", reports_dir)

        self.assertIn("_Generated on 2026-04-17_", markdown)
        self.assertIn("### to-date", markdown)

    def test_tools_get_window_metrics_returns_single_window(self) -> None:
        with make_reports_dir() as reports_dir:
            data = tools.get_window_metrics("Bravo", "to-date", reports_dir)

        self.assertEqual(data["podling"], "Bravo")
        self.assertEqual(data["window"], "to-date")
        self.assertEqual(data["metrics"]["commits"], 10)
        self.assertEqual(data["metrics"]["trends"]["commits"], "up")
        self.assertEqual(data["metrics"]["trends"]["median_merge_days"], "down")

    def test_tools_get_window_metrics_rejects_missing_window(self) -> None:
        with make_reports_dir() as reports_dir:
            with self.assertRaises(ValueError):
                tools.get_window_metrics("Alpha", "to-date", reports_dir)

    def test_tools_compare_windows_returns_requested_windows(self) -> None:
        with make_reports_dir() as reports_dir:
            data = tools.compare_windows("Alpha", ["3m", "6m"], reports_dir)

        self.assertEqual(data["podling"], "Alpha")
        self.assertEqual(set(data["windows"].keys()), {"3m", "6m"})
        self.assertEqual(data["windows"]["3m"]["commits"], 42)
        self.assertEqual(data["windows"]["6m"]["commits"], 70)
        self.assertEqual(data["windows"]["3m"]["trends"]["commits"], "up")
        self.assertEqual(data["windows"]["6m"]["trends"]["median_gap_days"], "flat")

    def test_tools_compare_windows_rejects_wrong_count(self) -> None:
        with self.assertRaises(ValueError):
            tools.compare_windows("Alpha", ["3m"], "reports")

    def test_tools_compare_windows_rejects_duplicates(self) -> None:
        with self.assertRaises(ValueError):
            tools.compare_windows("Alpha", ["3m", "3m"], "reports")

    def test_tools_compare_windows_rejects_missing_report_window(self) -> None:
        with make_reports_dir() as reports_dir:
            with self.assertRaises(ValueError):
                tools.compare_windows("Bravo", ["3m", "6m"], reports_dir)

    def test_tools_query_metric_rankings_applies_limit(self) -> None:
        with make_reports_dir() as reports_dir:
            data = tools.query_metric_rankings(
                metric="commits",
                window="3m",
                limit=1,
                reports_dir=reports_dir,
            )

        self.assertEqual(data["count"], 2)
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["results"][0]["podling"], "Alpha")

    def test_tools_list_metrics_returns_supported_values(self) -> None:
        data = tools.list_metrics()

        self.assertIn("commits", data["metrics"])
        self.assertIn("3m", data["windows"])

    def test_tools_uses_configured_reports_dir(self) -> None:
        with make_reports_dir() as reports_dir:
            tools.configure_reports_dir(reports_dir)
            data = tools.health_overview()

        self.assertEqual(data["report_count"], 2)
        self.assertEqual(data["reports_dir"], str(Path(reports_dir).resolve()))

    def test_reports_dir_must_be_string(self) -> None:
        with self.assertRaises(ValueError):
            tools.health_overview(123)  # type: ignore[arg-type]

    def test_query_must_be_non_empty_string(self) -> None:
        with self.assertRaises(ValueError):
            tools.search_podlings("   ", "reports")

    def test_podling_must_be_non_empty_string(self) -> None:
        with self.assertRaises(ValueError):
            tools.get_report_summary("   ", "reports")

    def test_metric_must_be_known(self) -> None:
        with self.assertRaises(ValueError):
            tools.query_metric_rankings(metric="unknown", reports_dir="reports")

    def test_window_must_be_known(self) -> None:
        with self.assertRaises(ValueError):
            tools.query_metric_rankings(metric="commits", window="1m", reports_dir="reports")

    def test_windows_must_be_known(self) -> None:
        with self.assertRaises(ValueError):
            tools.compare_windows("Alpha", ["3m", "1m"], "reports")

    def test_limit_must_be_positive_integer(self) -> None:
        with self.assertRaises(ValueError):
            tools.query_metric_rankings(metric="commits", limit=0, reports_dir="reports")

    def test_sort_desc_must_be_boolean(self) -> None:
        with self.assertRaises(ValueError):
            tools.query_metric_rankings(metric="commits", sort_desc="yes", reports_dir="reports")  # type: ignore[arg-type]

    def test_min_and_max_must_be_numbers(self) -> None:
        with self.assertRaises(ValueError):
            tools.query_metric_rankings(metric="commits", min_value="1", reports_dir="reports")  # type: ignore[arg-type]

    def test_min_must_not_exceed_max(self) -> None:
        with self.assertRaises(ValueError):
            tools.query_metric_rankings(
                metric="commits",
                min_value=10,
                max_value=1,
                reports_dir="reports",
            )
