"""Read-only access to completed benchmark report files."""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from jev_fhir.demo import DemoNotFoundError
from jev_fhir.logger import get_logger

REPORT_NAME_RE = re.compile(r"^bench_[0-9]{8}T[0-9]{6}Z$")
REPORT_FILE_RE = re.compile(r"^bench_[0-9]{8}T[0-9]{6}Z\.json$")


class BenchmarkSummary(BaseModel):
    """Metadata displayed for a completed benchmark report."""

    name: str
    generated_at: datetime
    mode: str
    dataset: str
    jev_model: str | None


def list_reports(results_dir: Path) -> list[BenchmarkSummary]:
    """Return valid benchmark-report summaries in newest-first filename order."""
    if not results_dir.is_dir():
        return []

    reports: list[BenchmarkSummary] = []
    report_paths = sorted(
        (path for path in results_dir.iterdir() if REPORT_FILE_RE.fullmatch(path.name)),
        key=lambda path: path.stem,
        reverse=True,
    )
    for path in report_paths:
        try:
            report = _read_report(path)
            reports.append(
                BenchmarkSummary(
                    name=path.stem,
                    generated_at=report["generated_at"],
                    mode=report["mode"],
                    dataset=report.get("dataset", "unit"),
                    jev_model=report.get("jev_model"),
                )
            )
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValidationError) as exc:
            get_logger().warning("benchmark_report_skipped", path=str(path), reason=str(exc))
    return reports


def load_report(results_dir: Path, name: str) -> dict[str, Any]:
    """Load one regex-validated report, raising a demo 404 when it does not exist."""
    if REPORT_NAME_RE.fullmatch(name) is None:
        raise DemoNotFoundError("benchmark report not found")
    path = results_dir / f"{name}.json"
    try:
        return _read_report(path)
    except FileNotFoundError as exc:
        raise DemoNotFoundError("benchmark report not found") from exc


def _read_report(path: Path) -> dict[str, Any]:
    """Read a JSON object from a benchmark report path."""
    report = json.loads(path.read_text())
    if not isinstance(report, dict):
        raise TypeError("benchmark report must contain a JSON object")
    return report
