from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from apache_health_mcp.parser import (
    find_report,
    load_reports,
    parse_report_text,
    query_metric,
    reports_overview,
    summarize_report,
)
from tests.fixtures import (
    ALPHA_REPORT,
    BRAVO_REPORT,
    MINIMAL_REPORT,
    NO_WINDOW_DETAILS_REPORT,
    make_reports_dir,
)


class ParserTests(unittest.TestCase):
    def test_parse_report_text_extracts_metrics(self) -> None:
        report = parse_report_text(ALPHA_REPORT, "Alpha", "/tmp/Alpha.md")

        self.assertEqual(report.generated_on, "2026-04-18")
        self.assertEqual([window.window for window in report.windows], ["3m", "6m"])

        short = report.windows[0]
        self.assertEqual(short.date_range, "2026-01-18 -> 2026-04-18")
        self.assertEqual(short.releases, 2)
        self.assertEqual(short.median_gap_days, 31.5)
        self.assertEqual(short.commits, 42)
        self.assertEqual(short.prs_merged, 10)
        self.assertEqual(short.median_merge_days, 2.5)
        self.assertEqual(short.reviewer_div_eff, 3.1)
        self.assertEqual(short.bus50, 2)
        self.assertEqual(short.dev_messages, 25)
        self.assertEqual(short.trends["releases"], "up")
        self.assertEqual(short.trends["median_gap_days"], "down")
        self.assertEqual(short.trends["commits"], "up")
        self.assertEqual(short.trends["issues_closed"], "down")
        self.assertEqual(short.trends["dev_unique_posters"], "flat")

    def test_parse_report_text_handles_em_dash_values(self) -> None:
        report = parse_report_text(BRAVO_REPORT, "Bravo", "/tmp/Bravo.md")

        short = report.windows[0]
        self.assertEqual(short.releases, 0)
        self.assertIsNone(short.median_gap_days)
        self.assertEqual(short.median_merge_days, 9.0)
        self.assertEqual(short.trends["median_gap_days"], "flat")
        self.assertEqual(short.trends["median_merge_days"], "up")

        to_date = report.windows[1]
        self.assertEqual(to_date.window, "to-date")
        self.assertIsNone(to_date.median_gap_days)
        self.assertEqual(to_date.trends["releases"], "up")
        self.assertEqual(to_date.trends["dev_messages"], "up")

    def test_parse_report_text_without_generated_on_or_windows(self) -> None:
        report = parse_report_text(MINIMAL_REPORT, "Minimal", "/tmp/Minimal.md")

        self.assertIsNone(report.generated_on)
        self.assertEqual(report.windows, [])

    def test_parse_report_text_without_window_details_section(self) -> None:
        report = parse_report_text(NO_WINDOW_DETAILS_REPORT, "NoWindow", "/tmp/NoWindow.md")

        self.assertEqual(report.generated_on, "2026-04-10")
        self.assertEqual(report.windows, [])

    def test_load_reports_ignores_summary_and_sorts(self) -> None:
        with make_reports_dir() as reports_dir:
            reports = load_reports(reports_dir)

        self.assertEqual([report.podling for report in reports], ["Alpha", "Bravo"])

    def test_load_reports_raises_for_missing_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "missing"
            with self.assertRaises(FileNotFoundError):
                load_reports(missing)

    def test_load_reports_raises_for_non_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "report.md"
            file_path.write_text(ALPHA_REPORT, encoding="utf-8")
            with self.assertRaises(NotADirectoryError):
                load_reports(file_path)

    def test_find_report_is_case_insensitive(self) -> None:
        with make_reports_dir() as reports_dir:
            report = find_report(reports_dir, "alpha")

        self.assertEqual(report.podling, "Alpha")
        self.assertEqual(report.generated_on, "2026-04-18")

    def test_find_report_raises_for_unknown_podling(self) -> None:
        with make_reports_dir() as reports_dir:
            with self.assertRaises(KeyError):
                find_report(reports_dir, "Unknown")

    def test_summarize_report_returns_window_map(self) -> None:
        with make_reports_dir() as reports_dir:
            report = find_report(reports_dir, "Bravo")
            summary = summarize_report(report)

        self.assertEqual(summary["podling"], "Bravo")
        self.assertEqual(summary["available_windows"], ["3m", "to-date"])
        self.assertEqual(summary["latest_metrics"]["3m"]["commits"], 8)
        self.assertEqual(summary["latest_metrics"]["3m"]["trends"]["commits"], "down")
        self.assertIsNone(summary["latest_metrics"]["6m"])
        self.assertEqual(summary["latest_metrics"]["to-date"]["releases"], 1)

    def test_reports_overview_returns_directory_metadata(self) -> None:
        with make_reports_dir() as reports_dir:
            overview = reports_overview(reports_dir)

        self.assertEqual(overview["report_count"], 2)
        self.assertEqual(overview["podlings"], ["Alpha", "Bravo"])
        self.assertEqual(overview["latest_generated_on"], "2026-04-18")

    def test_reports_overview_handles_empty_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            overview = reports_overview(temp_dir)

        self.assertEqual(overview["report_count"], 0)
        self.assertEqual(overview["podlings"], [])
        self.assertIsNone(overview["latest_generated_on"])

    def test_query_metric_ranks_and_filters(self) -> None:
        with make_reports_dir() as reports_dir:
            ranked = query_metric(reports_dir, metric="commits", window="3m")
            filtered = query_metric(reports_dir, metric="commits", window="3m", min_value=10)

        self.assertEqual([row["podling"] for row in ranked], ["Alpha", "Bravo"])
        self.assertEqual([row["value"] for row in ranked], [42, 8])
        self.assertEqual([row["podling"] for row in filtered], ["Alpha"])

    def test_query_metric_can_sort_ascending(self) -> None:
        with make_reports_dir() as reports_dir:
            ranked = query_metric(
                reports_dir, metric="median_merge_days", window="3m", sort_desc=False
            )

        self.assertEqual([row["podling"] for row in ranked], ["Alpha", "Bravo"])
        self.assertEqual([row["value"] for row in ranked], [2.5, 9.0])

    def test_query_metric_returns_empty_for_unknown_metric(self) -> None:
        with make_reports_dir() as reports_dir:
            result = query_metric(reports_dir, metric="does_not_exist", window="3m")

        self.assertEqual(result, [])

    def test_query_metric_returns_empty_for_unknown_window(self) -> None:
        with make_reports_dir() as reports_dir:
            result = query_metric(reports_dir, metric="commits", window="12m")

        self.assertEqual(result, [])
