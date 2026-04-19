from __future__ import annotations

import tempfile
from pathlib import Path

ALPHA_REPORT = """# Alpha - Incubator Health
_Generated on 2026-04-18_

## Window Details
### 3m  (2026-01-18 -> 2026-04-18)
- **Releases (from list votes/results):** 2 ↑  |  **Median gap (days):** 31.5 ↓
- **New contributors:** 4 ↑  |  **Unique committers:** 7 →  |  **Commits:** 42 ↑
- **Issues:** opened 9 ↑ / closed 8 ↓
- **PRs:** opened 12 ↑ / merged 10 ↑  |  **Median merge time (days):** 2.5 ↓
- **Reviews (sampled):** median reviewers/PR **2.0** →  |
  reviewer diversity (eff.#) **3.1** ↑  |
  PR author diversity (eff.#) **4.2** ↑  |
  unique reviewers **5** ↑, unique authors **6** →
- **Bus factor proxy (50% / 75%):** 2 ↑ / 4 →
- **Incubator reports:** 1 →  |  **Avg mentor sign-offs:** 2.0 ↑
- **Mailing lists:** dev messages **25** ↑, dev unique posters **9** →

### 6m  (2025-10-18 -> 2026-04-18)
- **Releases (from list votes/results):** 3 →  |  **Median gap (days):** 45 →
- **New contributors:** 6 ↑  |  **Unique committers:** 9 ↑  |  **Commits:** 70 ↑
- **Issues:** opened 14 ↑ / closed 11 ↑
- **PRs:** opened 20 ↑ / merged 16 ↑  |  **Median merge time (days):** 3.0 →
- **Reviews (sampled):** median reviewers/PR **2.0** →  |
  reviewer diversity (eff.#) **3.5** ↑  |
  PR author diversity (eff.#) **5.0** ↑  |
  unique reviewers **7** ↑, unique authors **8** ↑
- **Bus factor proxy (50% / 75%):** 3 ↑ / 5 ↑
- **Incubator reports:** 2 ↑  |  **Avg mentor sign-offs:** 2.5 ↑
- **Mailing lists:** dev messages **45** ↑, dev unique posters **12** ↑
"""

BRAVO_REPORT = """# Bravo - Incubator Health
_Generated on 2026-04-17_

## Window Details
### 3m  (2026-01-17 -> 2026-04-17)
- **Releases (from list votes/results):** 0 →  |  **Median gap (days):** — →
- **New contributors:** 1 ↓  |  **Unique committers:** 2 →  |  **Commits:** 8 ↓
- **Issues:** opened 2 → / closed 1 ↓
- **PRs:** opened 3 → / merged 2 ↓  |  **Median merge time (days):** 9.0 ↑
- **Reviews (sampled):** median reviewers/PR **1.0** →  |
  reviewer diversity (eff.#) **1.5** →  |
  PR author diversity (eff.#) **2.0** →  |
  unique reviewers **2** →, unique authors **2** →
- **Bus factor proxy (50% / 75%):** 1 → / 2 →
- **Incubator reports:** 1 →  |  **Avg mentor sign-offs:** 3.0 →
- **Mailing lists:** dev messages **6** ↓, dev unique posters **3** →

### to-date  (2026-02-01 -> 2026-04-17)
- **Releases (from list votes/results):** 1 ↑  |  **Median gap (days):** — →
- **New contributors:** 2 ↑  |  **Unique committers:** 2 →  |  **Commits:** 10 ↑
- **Issues:** opened 3 ↑ / closed 1 ↓
- **PRs:** opened 4 ↑ / merged 2 ↓  |  **Median merge time (days):** 7.0 ↓
- **Reviews (sampled):** median reviewers/PR **1.0** →  |
  reviewer diversity (eff.#) **1.5** →  |
  PR author diversity (eff.#) **2.0** →  |
  unique reviewers **2** →, unique authors **2** →
- **Bus factor proxy (50% / 75%):** 1 → / 2 →
- **Incubator reports:** 1 →  |  **Avg mentor sign-offs:** 3.0 →
- **Mailing lists:** dev messages **8** ↑, dev unique posters **3** →
"""

MINIMAL_REPORT = """# Minimal

No generated date here.
"""

NO_WINDOW_DETAILS_REPORT = """# NoWindow
_Generated on 2026-04-10_

## Something Else
This file is missing the expected section.
"""


def make_reports_dir() -> tempfile.TemporaryDirectory[str]:
    temp_dir = tempfile.TemporaryDirectory()
    path = Path(temp_dir.name)
    (path / "Alpha.md").write_text(ALPHA_REPORT, encoding="utf-8")
    (path / "Bravo.md").write_text(BRAVO_REPORT, encoding="utf-8")
    (path / "SUMMARY.md").write_text("# summary", encoding="utf-8")
    return temp_dir
