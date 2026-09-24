"""Run Jev decision modules and rule baselines against labelled fixtures."""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from statistics import fmean
from typing import Any, TypeVar, cast

from jev_fhir.baselines.bundle_router import route_bundle as rule_route_bundle
from jev_fhir.baselines.notifiable import is_notifiable as rule_is_notifiable
from jev_fhir.baselines.quality import score_patient as rule_score_patient
from jev_fhir.config import PROJECT_ROOT, Settings
from jev_fhir.dataset.labels import QualityLabel, load_labels
from jev_fhir.jev_client import JevClient, LiveJevClient, MockJevClient, RecordingJevClient
from jev_fhir.modules.bundle_router import BundleRouter
from jev_fhir.modules.notifiable_detector import NotifiableDiseaseDetector
from jev_fhir.modules.quality_scorer import QualityScorer

ROOT = PROJECT_ROOT
FIXTURES = ROOT / "tests" / "fixtures"
GROUND_TRUTH = ROOT / "benchmarks" / "ground_truth"
DISEASE_DATA = ROOT / "data" / "notifiable_diseases.json"
PRICE_PER_BILLION_TOKENS_USD = 42.0


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def percentile(values: list[float], percentile_value: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return round(ordered[min(len(ordered) - 1, round((len(ordered) - 1) * percentile_value))], 3)


def latency_metrics(values: list[float]) -> dict[str, float]:
    return {
        "mean_ms": round(fmean(values), 3) if values else 0.0,
        "p50_ms": percentile(values, 0.5),
        "p95_ms": percentile(values, 0.95),
    }


def calibration(decisions: list[tuple[float, bool]]) -> list[dict[str, float | int | str]]:
    report: list[dict[str, float | int | str]] = []
    for lower, upper in ((0.0, 0.5), (0.5, 0.8), (0.8, 1.01)):
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


def accuracy(rows: list[dict[str, Any]], field: str) -> float:
    return round(fmean(float(bool(row[field])) for row in rows), 3) if rows else 0.0


T = TypeVar("T")


def limited(items: list[T], limit: int | None) -> list[T]:
    return items if limit is None else items[:limit]


def make_client(live: bool, settings: Settings) -> tuple[JevClient, str, str | None]:
    if not live:
        return MockJevClient(), "mock_jev", None
    return (
        LiveJevClient(
            settings.jev_api_key,
            settings.jev_base_url,
            model=settings.jev_model,
            timeout_s=settings.jev_timeout_s,
            max_retries=settings.jev_max_retries,
            retry_budget_s=settings.jev_retry_budget_s,
        ),
        "live_jev",
        settings.jev_model,
    )


async def run_benchmark(*, live: bool = False, limit: int | None = None) -> dict[str, Any]:
    """Run the unit dataset using mock mode by default and live Jev on demand."""
    settings = Settings()
    inner_client, mode, model = make_client(live, settings)
    quality_labels = limited(load_labels(settings.labels_dir / "quality.json", QualityLabel), limit)
    route_labels = limited(
        cast(list[dict[str, Any]], load_json(GROUND_TRUTH / "bundle_routes.json")), limit
    )
    disease_labels = limited(
        cast(list[dict[str, Any]], load_json(GROUND_TRUTH / "notifiable_diseases.json")), limit
    )
    all_tokens = 0
    try:
        quality_rows: list[dict[str, Any]] = []
        quality_latencies: list[float] = []
        quality_confidence: list[tuple[float, bool]] = []
        score_in_band: list[bool] = []
        for label in quality_labels:
            resource = cast(dict[str, Any], load_json(ROOT / label.fixture))
            recording = RecordingJevClient(inner_client)
            result = await QualityScorer(recording).score(resource, label.resource_type)
            baseline = rule_score_patient(resource)
            baseline_score = baseline["score"]
            if not isinstance(baseline_score, int):
                raise TypeError("rule quality baseline must return an integer score")
            lower, upper = label.expected_score_range
            jev_correct = result.action == label.expected_action
            rule_action = "auto_accept" if baseline_score >= 70 else "review_needed"
            rule_correct = rule_action == label.expected_action
            calls = recording.drain()
            row_tokens = sum(call.result.tokens_used for call in calls)
            all_tokens += row_tokens
            quality_rows.append(
                {
                    "fixture": label.fixture,
                    "expected_action": label.expected_action,
                    "expected_score_range": [lower, upper],
                    "jev_action": result.action,
                    "rule_action": rule_action,
                    "jev_score": result.score,
                    "rule_score": baseline_score,
                    "jev_correct": jev_correct,
                    "rule_correct": rule_correct,
                    "jev_score_in_band": lower <= result.score <= upper,
                    "rule_score_in_band": lower <= baseline_score <= upper,
                    "tokens_used": row_tokens,
                    "jev_latency_ms": round(sum(call.result.latency_ms for call in calls), 3),
                    "jev_confidence": result.confidence,
                }
            )
            quality_latencies.append(result.latency_ms)
            quality_confidence.append((result.confidence, jev_correct))
            score_in_band.append(lower <= result.score <= upper)

        route_rows: list[dict[str, Any]] = []
        route_latencies: list[float] = []
        route_confidence: list[tuple[float, bool]] = []
        for route_label in route_labels:
            fixture = str(route_label["fixture"])
            bundle = cast(dict[str, Any], load_json(FIXTURES / fixture))
            recording = RecordingJevClient(inner_client)
            route_result = await BundleRouter(recording).route(bundle)
            expected_category = str(route_label["expected_category"])
            calls = recording.drain()
            row_tokens = sum(call.result.tokens_used for call in calls)
            all_tokens += row_tokens
            rule_category = rule_route_bundle(bundle)
            jev_correct = route_result.category == expected_category
            route_rows.append(
                {
                    "fixture": fixture,
                    "expected_category": expected_category,
                    "jev_category": route_result.category,
                    "rule_category": rule_category,
                    "jev_correct": jev_correct,
                    "rule_correct": rule_category == expected_category,
                    "tokens_used": row_tokens,
                    "jev_latency_ms": round(sum(call.result.latency_ms for call in calls), 3),
                    "jev_confidence": route_result.confidence,
                }
            )
            route_latencies.append(route_result.latency_ms)
            route_confidence.append((route_result.confidence, jev_correct))

        disease_rows: list[dict[str, Any]] = []
        disease_latencies: list[float] = []
        disease_confidence: list[tuple[float, bool]] = []
        disease_predictions: list[bool] = []
        rule_predictions: list[bool] = []
        disease_expected: list[bool] = []
        for disease_label in disease_labels:
            fixture = str(disease_label["fixture"])
            condition = cast(dict[str, Any], load_json(FIXTURES / fixture))
            recording = RecordingJevClient(inner_client)
            disease_result = await NotifiableDiseaseDetector(recording).detect(condition)
            expected_notifiable = bool(disease_label["expected_notifiable"])
            rule_result = rule_is_notifiable(condition, DISEASE_DATA)
            calls = recording.drain()
            row_tokens = sum(call.result.tokens_used for call in calls)
            all_tokens += row_tokens
            jev_correct = disease_result.is_notifiable == expected_notifiable
            disease_rows.append(
                {
                    "fixture": fixture,
                    "expected_notifiable": expected_notifiable,
                    "jev_notifiable": disease_result.is_notifiable,
                    "rule_notifiable": rule_result,
                    "jev_correct": jev_correct,
                    "rule_correct": rule_result == expected_notifiable,
                    "tokens_used": row_tokens,
                    "jev_latency_ms": round(sum(call.result.latency_ms for call in calls), 3),
                    "jev_confidence": disease_result.probability,
                }
            )
            disease_latencies.append(disease_result.latency_ms)
            disease_confidence.append((disease_result.probability, jev_correct))
            disease_predictions.append(disease_result.is_notifiable)
            rule_predictions.append(rule_result)
            disease_expected.append(expected_notifiable)

        billed_tokens = all_tokens if live else 0
        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "mode": mode,
            "jev_model": model,
            "dataset": "unit",
            "quality_labels_banded": True,
            "token_and_cost": {
                "tokens_used": billed_tokens,
                "estimated_cost_usd": round(
                    billed_tokens * PRICE_PER_BILLION_TOKENS_USD / 1_000_000_000, 8
                ),
                "pricing_note": "total tokens × $42 / 1e9",
            },
            "modules": {
                "quality_scorer": {
                    "fixture_count": len(quality_rows),
                    "jev_accuracy": accuracy(quality_rows, "jev_correct"),
                    "rule_accuracy": accuracy(quality_rows, "rule_correct"),
                    "jev_score_in_band": round(fmean(score_in_band), 3) if score_in_band else 0.0,
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
                        disease_predictions, disease_expected
                    ),
                    "rule_precision_recall_f1": binary_metrics(rule_predictions, disease_expected),
                    "latency": latency_metrics(disease_latencies),
                    "confidence_calibration": calibration(disease_confidence),
                    "rows": disease_rows,
                },
            },
        }
    finally:
        if isinstance(inner_client, LiveJevClient):
            await inner_client.aclose()


def markdown_report(results: dict[str, Any]) -> str:
    modules = cast(dict[str, dict[str, Any]], results["modules"])
    lines = [
        "# Jev × FHIR Benchmark Report",
        "",
        f"Generated: {results['generated_at']}",
        f"Mode: {results['mode']}",
        f"Dataset: {results['dataset']}",
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
    lines.extend(["", f"Token/cost accounting: {results['token_and_cost']}"])
    return "\n".join(lines) + "\n"


def write_reports(results: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    json_path = output_dir / f"bench_{suffix}.json"
    markdown_path = output_dir / f"bench_{suffix}.md"
    json_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(markdown_report(results), encoding="utf-8")
    return json_path, markdown_path


async def async_main(
    output_dir: Path, *, live: bool = False, limit: int | None = None
) -> tuple[Path, Path]:
    return write_reports(await run_benchmark(live=live, limit=limit), output_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "benchmarks" / "results")
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    json_path, markdown_path = asyncio.run(
        async_main(args.output_dir, live=args.live, limit=args.limit)
    )
    print(f"Wrote {json_path}")
    print(f"Wrote {markdown_path}")


if __name__ == "__main__":
    main()
