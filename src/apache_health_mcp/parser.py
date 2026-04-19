from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

GENERATED_ON_RE = re.compile(r"_Generated on\s+(\d{4}-\d{2}-\d{2})_", re.IGNORECASE)
WINDOW_HEADER_RE = re.compile(r"^###\s+(3m|6m|12m|to-date)\b(?:\s+\(([^)]*)\))?", re.MULTILINE)
TREND_ARROW_CLASS = r"[↑↓→↔↗↘↙↖▲▼▶◀]"
TREND_ARROW_RE = rf"({TREND_ARROW_CLASS})"
OPTIONAL_TREND_RE = rf"(?:\s*{TREND_ARROW_CLASS})?"
TREND_LABELS = {
    "↑": "up",
    "▲": "up",
    "↗": "up",
    "↓": "down",
    "▼": "down",
    "↘": "down",
    "→": "flat",
    "↔": "flat",
    "▶": "flat",
    "◀": "flat",
    "↙": "mixed",
    "↖": "mixed",
}

RE_RELEASES = re.compile(
    rf"Releases .*?:\s*(\d+){OPTIONAL_TREND_RE}\s*\|\s*"
    rf"Median gap \(days\):\s*([0-9.]+|—){OPTIONAL_TREND_RE}"
)
RE_CONTRIB = re.compile(
    rf"New contributors:\s*(\d+){OPTIONAL_TREND_RE}\s*\|\s*"
    rf"Unique committers:\s*(\d+){OPTIONAL_TREND_RE}\s*\|\s*"
    rf"Commits:\s*(\d+){OPTIONAL_TREND_RE}"
)
RE_ISSUES = re.compile(
    rf"Issues:\s*opened\s*(\d+){OPTIONAL_TREND_RE}\s*/\s*closed\s*(\d+){OPTIONAL_TREND_RE}"
)
RE_PRS = re.compile(
    rf"PRs:\s*opened\s*(\d+){OPTIONAL_TREND_RE}\s*/\s*"
    rf"merged\s*(\d+){OPTIONAL_TREND_RE}\s*\|\s*"
    rf"Median merge time \(days\):\s*([0-9.]+|—){OPTIONAL_TREND_RE}"
)
RE_REVIEWS = re.compile(
    rf"Reviews \(sampled\):.*?median reviewers/PR\s*([0-9.]+|—){OPTIONAL_TREND_RE}.*?"
    rf"reviewer diversity \(eff\.\#\)\s*([0-9.]+|—){OPTIONAL_TREND_RE}.*?"
    rf"PR author diversity \(eff\.\#\)\s*([0-9.]+|—){OPTIONAL_TREND_RE}.*?"
    rf"unique reviewers\s*(\d+|—){OPTIONAL_TREND_RE},\s*unique authors\s*(\d+|—){OPTIONAL_TREND_RE}"
)
RE_BUS = re.compile(
    rf"Bus factor proxy \(50%\s*/\s*75%\):\s*(\d+|—){OPTIONAL_TREND_RE}\s*/\s*"
    rf"(\d+|—){OPTIONAL_TREND_RE}"
)
RE_REPORTS = re.compile(
    rf"Incubator reports:\s*(\d+|—){OPTIONAL_TREND_RE}\s*\|\s*"
    rf"Avg mentor sign-offs:\s*([0-9.]+|—){OPTIONAL_TREND_RE}"
)
RE_MAIL = re.compile(
    rf"Mailing lists:\s*dev messages\s*(\d+|—){OPTIONAL_TREND_RE},\s*"
    rf"dev unique posters\s*(\d+|—){OPTIONAL_TREND_RE}"
)


def _to_int(value: str | None) -> int | None:
    if value is None or value == "—":
        return None
    return int(value)


def _to_float(value: str | None) -> float | None:
    if value is None or value == "—":
        return None
    return float(value)


def _trend_label(value: str) -> str:
    return TREND_LABELS.get(value, "unknown")


@dataclass
class WindowMetrics:
    window: str
    date_range: str | None
    releases: int | None = None
    median_gap_days: float | None = None
    new_contributors: int | None = None
    unique_committers: int | None = None
    commits: int | None = None
    issues_opened: int | None = None
    issues_closed: int | None = None
    prs_opened: int | None = None
    prs_merged: int | None = None
    median_merge_days: float | None = None
    median_reviewers_per_pr: float | None = None
    reviewer_div_eff: float | None = None
    pr_author_div_eff: float | None = None
    unique_reviewers: int | None = None
    unique_authors: int | None = None
    bus50: int | None = None
    bus75: int | None = None
    reports_count: int | None = None
    avg_mentor_signoffs: float | None = None
    dev_messages: int | None = None
    dev_unique_posters: int | None = None
    trends: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ParsedReport:
    podling: str
    path: str
    generated_on: str | None
    windows: list[WindowMetrics]
    raw_text: str

    def to_dict(self, include_raw: bool = False) -> dict[str, Any]:
        data = {
            "podling": self.podling,
            "path": self.path,
            "generated_on": self.generated_on,
            "windows": [window.to_dict() for window in self.windows],
        }
        if include_raw:
            data["raw_text"] = self.raw_text
        return data


def parse_report_text(text: str, podling: str, path: str) -> ParsedReport:
    generated = GENERATED_ON_RE.search(text)
    generated_on = generated.group(1) if generated else None

    window_section_index = text.find("## Window Details")
    window_source = text[window_section_index:] if window_section_index >= 0 else text
    matches = list(WINDOW_HEADER_RE.finditer(window_source))
    windows: list[WindowMetrics] = []

    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(window_source)
        block = window_source[start:end]
        metrics = WindowMetrics(window=match.group(1), date_range=match.group(2))
        bullet_lines: list[str] = []
        current_line: str | None = None

        for raw_line in block.splitlines():
            stripped = raw_line.strip()
            if not stripped:
                continue
            if stripped.startswith("- "):
                if current_line is not None:
                    bullet_lines.append(current_line.replace("**", ""))
                current_line = stripped
            elif current_line is not None:
                current_line = f"{current_line} {stripped}"

        if current_line is not None:
            bullet_lines.append(current_line.replace("**", ""))

        for line in bullet_lines:
            body = line[2:].strip()

            if body.startswith("Releases "):
                result = RE_RELEASES.search(body)
                if result:
                    metrics.releases = _to_int(result.group(1))
                    metrics.median_gap_days = _to_float(result.group(2))
                for field_name, pattern in (
                    ("releases", rf"Releases .*?:\s*\d+\s*{TREND_ARROW_RE}"),
                    (
                        "median_gap_days",
                        rf"Median gap \(days\):\s*(?:[0-9.]+|—)\s*{TREND_ARROW_RE}",
                    ),
                ):
                    trend = re.search(pattern, body)
                    if trend:
                        metrics.trends[field_name] = _trend_label(trend.group(1))
            elif body.startswith("New contributors:"):
                result = RE_CONTRIB.search(body)
                if result:
                    metrics.new_contributors = _to_int(result.group(1))
                    metrics.unique_committers = _to_int(result.group(2))
                    metrics.commits = _to_int(result.group(3))
                for field_name, pattern in (
                    ("new_contributors", rf"New contributors:\s*\d+\s*{TREND_ARROW_RE}"),
                    ("unique_committers", rf"Unique committers:\s*\d+\s*{TREND_ARROW_RE}"),
                    ("commits", rf"Commits:\s*\d+\s*{TREND_ARROW_RE}"),
                ):
                    trend = re.search(pattern, body)
                    if trend:
                        metrics.trends[field_name] = _trend_label(trend.group(1))
            elif body.startswith("Issues:"):
                result = RE_ISSUES.search(body)
                if result:
                    metrics.issues_opened = _to_int(result.group(1))
                    metrics.issues_closed = _to_int(result.group(2))
                for field_name, pattern in (
                    ("issues_opened", rf"opened\s*\d+\s*{TREND_ARROW_RE}"),
                    ("issues_closed", rf"closed\s*\d+\s*{TREND_ARROW_RE}"),
                ):
                    trend = re.search(pattern, body)
                    if trend:
                        metrics.trends[field_name] = _trend_label(trend.group(1))
            elif body.startswith("PRs:"):
                result = RE_PRS.search(body)
                if result:
                    metrics.prs_opened = _to_int(result.group(1))
                    metrics.prs_merged = _to_int(result.group(2))
                    metrics.median_merge_days = _to_float(result.group(3))
                for field_name, pattern in (
                    ("prs_opened", rf"opened\s*\d+\s*{TREND_ARROW_RE}"),
                    ("prs_merged", rf"merged\s*\d+\s*{TREND_ARROW_RE}"),
                    (
                        "median_merge_days",
                        rf"Median merge time \(days\):\s*(?:[0-9.]+|—)\s*{TREND_ARROW_RE}",
                    ),
                ):
                    trend = re.search(pattern, body)
                    if trend:
                        metrics.trends[field_name] = _trend_label(trend.group(1))
            elif body.startswith("Reviews (sampled):"):
                result = RE_REVIEWS.search(body)
                if result:
                    metrics.median_reviewers_per_pr = _to_float(result.group(1))
                    metrics.reviewer_div_eff = _to_float(result.group(2))
                    metrics.pr_author_div_eff = _to_float(result.group(3))
                    metrics.unique_reviewers = _to_int(result.group(4))
                    metrics.unique_authors = _to_int(result.group(5))
                for field_name, pattern in (
                    (
                        "median_reviewers_per_pr",
                        rf"median reviewers/PR\s*(?:[0-9.]+|—)\s*{TREND_ARROW_RE}",
                    ),
                    (
                        "reviewer_div_eff",
                        rf"reviewer diversity \(eff\.\#\)\s*(?:[0-9.]+|—)\s*{TREND_ARROW_RE}",
                    ),
                    (
                        "pr_author_div_eff",
                        rf"PR author diversity \(eff\.\#\)\s*(?:[0-9.]+|—)\s*{TREND_ARROW_RE}",
                    ),
                    (
                        "unique_reviewers",
                        rf"unique reviewers\s*(?:\d+|—)\s*{TREND_ARROW_RE}",
                    ),
                    ("unique_authors", rf"unique authors\s*(?:\d+|—)\s*{TREND_ARROW_RE}"),
                ):
                    trend = re.search(pattern, body)
                    if trend:
                        metrics.trends[field_name] = _trend_label(trend.group(1))
            elif body.startswith("Bus factor proxy"):
                result = RE_BUS.search(body)
                if result:
                    metrics.bus50 = _to_int(result.group(1))
                    metrics.bus75 = _to_int(result.group(2))
                for field_name, pattern in (
                    (
                        "bus50",
                        rf"Bus factor proxy \(50%\s*/\s*75%\):\s*(?:\d+|—)\s*{TREND_ARROW_RE}",
                    ),
                    ("bus75", rf"/\s*(?:\d+|—)\s*{TREND_ARROW_RE}"),
                ):
                    trend = re.search(pattern, body)
                    if trend:
                        metrics.trends[field_name] = _trend_label(trend.group(1))
            elif body.startswith("Incubator reports:"):
                result = RE_REPORTS.search(body)
                if result:
                    metrics.reports_count = _to_int(result.group(1))
                    metrics.avg_mentor_signoffs = _to_float(result.group(2))
                for field_name, pattern in (
                    ("reports_count", rf"Incubator reports:\s*(?:\d+|—)\s*{TREND_ARROW_RE}"),
                    (
                        "avg_mentor_signoffs",
                        rf"Avg mentor sign-offs:\s*(?:[0-9.]+|—)\s*{TREND_ARROW_RE}",
                    ),
                ):
                    trend = re.search(pattern, body)
                    if trend:
                        metrics.trends[field_name] = _trend_label(trend.group(1))
            elif body.startswith("Mailing lists:"):
                result = RE_MAIL.search(body)
                if result:
                    metrics.dev_messages = _to_int(result.group(1))
                    metrics.dev_unique_posters = _to_int(result.group(2))
                for field_name, pattern in (
                    ("dev_messages", rf"dev messages\s*(?:\d+|—)\s*{TREND_ARROW_RE}"),
                    (
                        "dev_unique_posters",
                        rf"dev unique posters\s*(?:\d+|—)\s*{TREND_ARROW_RE}",
                    ),
                ):
                    trend = re.search(pattern, body)
                    if trend:
                        metrics.trends[field_name] = _trend_label(trend.group(1))

        windows.append(metrics)

    return ParsedReport(
        podling=podling,
        path=path,
        generated_on=generated_on,
        windows=windows,
        raw_text=text,
    )


def is_report_file(path: Path) -> bool:
    return path.suffix.lower() == ".md" and path.stem.casefold() != "summary"


def load_reports(reports_dir: str | Path) -> list[ParsedReport]:
    base = Path(reports_dir).expanduser().resolve()
    if not base.exists():
        raise FileNotFoundError(f"Reports directory does not exist: {base}")
    if not base.is_dir():
        raise NotADirectoryError(f"Reports path is not a directory: {base}")

    reports: list[ParsedReport] = []
    for path in sorted(base.glob("*.md")):
        if not is_report_file(path):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        reports.append(parse_report_text(text=text, podling=path.stem, path=str(path)))
    return reports


def list_podlings(reports_dir: str | Path) -> list[str]:
    return [report.podling for report in load_reports(reports_dir)]


def find_report(reports_dir: str | Path, podling: str) -> ParsedReport:
    normalized = podling.casefold()
    for report in load_reports(reports_dir):
        if report.podling.casefold() == normalized:
            return report
    raise KeyError(f"No report found for podling: {podling}")


def latest_generated_on(reports: list[ParsedReport]) -> str | None:
    values = [report.generated_on for report in reports if report.generated_on]
    if not values:
        return None
    return max(values)


def summarize_report(report: ParsedReport) -> dict[str, Any]:
    by_window = {window.window: window for window in report.windows}
    return {
        "podling": report.podling,
        "path": report.path,
        "generated_on": report.generated_on,
        "available_windows": [window.window for window in report.windows],
        "latest_metrics": {
            "3m": by_window["3m"].to_dict() if "3m" in by_window else None,
            "6m": by_window["6m"].to_dict() if "6m" in by_window else None,
            "12m": by_window["12m"].to_dict() if "12m" in by_window else None,
            "to-date": by_window["to-date"].to_dict() if "to-date" in by_window else None,
        },
    }


def query_metric(
    reports_dir: str | Path,
    metric: str,
    window: str,
    min_value: float | None = None,
    max_value: float | None = None,
    sort_desc: bool = True,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for report in load_reports(reports_dir):
        for metrics in report.windows:
            if metrics.window != window:
                continue
            value = getattr(metrics, metric, None)
            if value is None:
                continue
            if min_value is not None and value < min_value:
                continue
            if max_value is not None and value > max_value:
                continue
            rows.append(
                {
                    "podling": report.podling,
                    "generated_on": report.generated_on,
                    "window": metrics.window,
                    "metric": metric,
                    "value": value,
                    "path": report.path,
                }
            )
    return sorted(rows, key=lambda row: row["value"], reverse=sort_desc)


def reports_overview(reports_dir: str | Path) -> dict[str, Any]:
    reports = load_reports(reports_dir)
    return {
        "reports_dir": str(Path(reports_dir).expanduser().resolve()),
        "report_count": len(reports),
        "podlings": sorted(report.podling for report in reports),
        "latest_generated_on": latest_generated_on(reports),
    }
