"""Run Jev decision modules and rule baselines against labeled synthetic fixtures."""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from statistics import fmean
from typing import Any, cast

from benchmarks.baselines.rule_bundle_router import route_bundle as rule_route_bundle
from benchmarks.baselines.rule_notifiable_detector import is_notifiable as rule_is_notifiable
from benchmarks.baselines.rule_quality_scorer import score_patient as rule_score_patient
from jev_fhir.jev_client.mock import MockJevClient
from jev_fhir.modules.bundle_router import BundleRouter
from jev_fhir.modules.notifiable_detector import NotifiableDiseaseDetector
from jev_fhir.modules.quality_scorer import QualityScorer

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
GROUND_TRUTH = ROOT / "benchmarks" / "ground_truth"
DISEASE_DATA = ROOT / "data" / "notifiable_diseases.json"


def load_json(path: Path) -> Any:
    """Load a JSON document from a known local benchmark path."""
    with path.open(encoding="utf-8") as input_file:
        return json.load(input_file)


def percentile(values: list[float], percentile_value: float) -> float:
    """Return a nearest-rank percentile for a non-empty latency collection."""
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, round((len(ordered) - 1) * percentile_value))
    return round(ordered[index], 3)


def latency_metrics(values: list[float]) -> dict[str, float]:
    """Compute the latency summary used in the JSON and Markdown reports."""
    return {
        "mean_ms": round(fmean(values), 3) if values else 0.0,
        "p50_ms": percentile(values, 0.50),
        "p95_ms": percentile(values, 0.95),
    }


def calibration(decisions: list[tuple[float, bool]]) -> list[dict[str, float | int | str]]:
    """Compare stated confidence with observed correctness in fixed confidence buckets."""
    buckets = [(0.0, 0.5), (0.5, 0.8), (0.8, 1.01)]
    report: list[dict[str, float | int | str]] = []
    for lower, upper in buckets:
        members = [
            (confidence, correct)
            for confidence, correct in decisions
            if lower <= confidence < upper
        ]
        if members:
            report.append(
                {
                    "bucket": f"{lower:.1f}-{min(upper, 1.0):.1f}",
                    "count": len(members),
                    "mean_confidence": round(fmean(item[0] for item in members), 3),
                    "observed_accuracy": round(fmean(float(item[1]) for item in members), 3),
                }
            )
    return report


def binary_metrics(predictions: list[bool], expected: list[bool]) -> dict[str, float]:
    """Compute precision, recall, and F1 for positive notifiable-disease cases."""
    true_positive = sum(
        prediction and label for prediction, label in zip(predictions, expected, strict=True)
    )
    false_positive = sum(
        prediction and not label for prediction, label in zip(predictions, expected, strict=True)
    )
    false_negative = sum(
        not prediction and label for prediction, label in zip(predictions, expected, strict=True)
    )
    precision = (
        true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
    )
    recall = (
        true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
    )
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": round(precision, 3), "recall": round(recall, 3), "f1": round(f1, 3)}


async def run_benchmark() -> dict[str, Any]:
    """Run every labeled fixture through Jev's mock modules and the rule baselines."""
    quality_labels = cast(list[dict[str, Any]], load_json(GROUND_TRUTH / "quality_scores.json"))
    route_labels = cast(list[dict[str, Any]], load_json(GROUND_TRUTH / "bundle_routes.json"))
    disease_labels = cast(
        list[dict[str, Any]], load_json(GROUND_TRUTH / "notifiable_diseases.json")
    )

    mock_client = MockJevClient()
    quality_scorer = QualityScorer(mock_client)
    bundle_router = BundleRouter(mock_client)
    detector = NotifiableDiseaseDetector(mock_client)

    quality_rows: list[dict[str, Any]] = []
    quality_latencies: list[float] = []
    quality_confidence: list[tuple[float, bool]] = []
    for label in quality_labels:
        fixture = str(label["fixture"])
        resource = cast(dict[str, Any], load_json(FIXTURES / fixture))
        quality_jev_result = await quality_scorer.score(resource, "Patient")
        baseline_result = rule_score_patient(resource)
        baseline_score = baseline_result["score"]
        if not isinstance(baseline_score, int):
            raise TypeError("rule quality baseline must return an integer score")
        lower, upper = cast(list[int], label["expected_score_range"])
        expected_nik = label["expected_nik_valid"]
        jev_correct = lower <= quality_jev_result.score <= upper and (
            expected_nik is None or quality_jev_result.nik_valid == expected_nik
        )
        baseline_correct = lower <= baseline_score <= upper and (
            expected_nik is None or baseline_result["nik_valid"] == expected_nik
        )
        quality_rows.append(
            {
                "fixture": fixture,
                "expected_score_range": [lower, upper],
                "jev_score": quality_jev_result.score,
                "rule_score": baseline_score,
                "jev_correct": jev_correct,
                "rule_correct": baseline_correct,
            }
        )
        quality_latencies.append(quality_jev_result.latency_ms)
        quality_confidence.append((quality_jev_result.confidence, jev_correct))

    route_rows: list[dict[str, Any]] = []
    route_latencies: list[float] = []
    route_confidence: list[tuple[float, bool]] = []
    for label in route_labels:
        fixture = str(label["fixture"])
        bundle = cast(dict[str, Any], load_json(FIXTURES / fixture))
        route_jev_result = await bundle_router.route(bundle)
        rule_result = rule_route_bundle(bundle)
        expected = str(label["expected_category"])
        jev_correct = route_jev_result.category == expected
        baseline_correct = rule_result == expected
        route_rows.append(
            {
                "fixture": fixture,
                "expected_category": expected,
                "jev_category": route_jev_result.category,
                "rule_category": rule_result,
                "jev_correct": jev_correct,
                "rule_correct": baseline_correct,
            }
        )
        route_latencies.append(route_jev_result.latency_ms)
        route_confidence.append((route_jev_result.confidence, jev_correct))

    disease_rows: list[dict[str, Any]] = []
    disease_latencies: list[float] = []
    disease_confidence: list[tuple[float, bool]] = []
    disease_jev_predictions: list[bool] = []
    disease_rule_predictions: list[bool] = []
    disease_expected: list[bool] = []
    for label in disease_labels:
        fixture = str(label["fixture"])
        condition = cast(dict[str, Any], load_json(FIXTURES / fixture))
        disease_jev_result = await detector.detect(condition)
        disease_rule_result = rule_is_notifiable(condition, DISEASE_DATA)
        disease_expected_value = bool(label["expected_notifiable"])
        jev_correct = disease_jev_result.is_notifiable == disease_expected_value
        baseline_correct = disease_rule_result == disease_expected_value
        disease_rows.append(
            {
                "fixture": fixture,
                "expected_notifiable": disease_expected_value,
                "jev_notifiable": disease_jev_result.is_notifiable,
                "rule_notifiable": disease_rule_result,
                "jev_correct": jev_correct,
                "rule_correct": baseline_correct,
            }
        )
        disease_latencies.append(disease_jev_result.latency_ms)
        disease_confidence.append((disease_jev_result.probability, jev_correct))
        disease_jev_predictions.append(disease_jev_result.is_notifiable)
        disease_rule_predictions.append(disease_rule_result)
        disease_expected.append(disease_expected_value)

    def accuracy(rows: list[dict[str, Any]], field: str) -> float:
        return round(fmean(float(bool(row[field])) for row in rows), 3)

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "mode": "mock_jev",
        "token_and_cost": {"tokens_used": 0, "estimated_cost_usd": 0.0, "note": "mock client"},
        "modules": {
            "quality_scorer": {
                "fixture_count": len(quality_rows),
                "jev_accuracy": accuracy(quality_rows, "jev_correct"),
                "rule_accuracy": accuracy(quality_rows, "rule_correct"),
                "latency": latency_metrics(quality_latencies),
                "confidence_calibration": calibration(quality_confidence),
                "rows": quality_rows,
            },
            "bundle_router": {
                "fixture_count": len(route_rows),
                "jev_accuracy": accuracy(route_rows, "jev_correct"),
                "rule_accuracy": accuracy(route_rows, "rule_correct"),
                "latency": latency_metrics(route_latencies),
                "confidence_calibration": calibration(route_confidence),
                "rows": route_rows,
            },
            "notifiable_detector": {
                "fixture_count": len(disease_rows),
                "jev_accuracy": accuracy(disease_rows, "jev_correct"),
                "rule_accuracy": accuracy(disease_rows, "rule_correct"),
                "jev_precision_recall_f1": binary_metrics(
                    disease_jev_predictions, disease_expected
                ),
                "rule_precision_recall_f1": binary_metrics(
                    disease_rule_predictions, disease_expected
                ),
                "latency": latency_metrics(disease_latencies),
                "confidence_calibration": calibration(disease_confidence),
                "rows": disease_rows,
            },
        },
    }


def markdown_report(results: dict[str, Any]) -> str:
    """Render a concise Jev-versus-rule benchmark summary."""
    modules = cast(dict[str, dict[str, Any]], results["modules"])
    lines = [
        "# Jev × FHIR Benchmark Report",
        "",
        f"Generated: {results['generated_at']}",
        f"Mode: {results['mode']}",
        "",
        "| Module | Fixtures | Jev accuracy | Rule accuracy | Mean ms | P50 ms | P95 ms |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, result in modules.items():
        latency = cast(dict[str, float], result["latency"])
        lines.append(
            f"| {name} | {result['fixture_count']} | {result['jev_accuracy']:.3f} | "
            f"{result['rule_accuracy']:.3f} | {latency['mean_ms']:.3f} | "
            f"{latency['p50_ms']:.3f} | {latency['p95_ms']:.3f} |"
        )
    detection = modules["notifiable_detector"]
    lines.extend(
        [
            "",
            "## Notifiable Disease Detection",
            "",
            f"Jev precision/recall/F1: {detection['jev_precision_recall_f1']}",
            f"Rule precision/recall/F1: {detection['rule_precision_recall_f1']}",
            "",
            f"Token/cost accounting: {results['token_and_cost']}",
        ]
    )
    return "\n".join(lines) + "\n"


def write_reports(results: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    """Write timestamped structured and Markdown benchmark outputs."""
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    json_path = output_dir / f"bench_{suffix}.json"
    markdown_path = output_dir / f"bench_{suffix}.md"
    json_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(markdown_report(results), encoding="utf-8")
    return json_path, markdown_path


async def async_main(output_dir: Path) -> tuple[Path, Path]:
    """Run and persist the complete benchmark."""
    results = await run_benchmark()
    return write_reports(results, output_dir)


def main() -> None:
    """CLI entry point used by ``make bench``."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "benchmarks" / "results")
    args = parser.parse_args()
    json_path, markdown_path = asyncio.run(async_main(args.output_dir))
    print(f"Wrote {json_path}")
    print(f"Wrote {markdown_path}")


if __name__ == "__main__":
    main()
