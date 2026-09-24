"""Allow-listed fixture catalog built from the D0.5 label files."""

import json
from pathlib import Path
from typing import Any, TypeVar, cast

from jev_fhir.dataset.labels import (
    Difficulty,
    LabelBase,
    NotifiableLabel,
    QualityLabel,
    RouteLabel,
    Source,
    fixture_path,
    load_labels,
)
from jev_fhir.demo.schemas import DemoModule, FixtureEntry

LabelT = TypeVar("LabelT", bound=LabelBase)


class FixtureCatalog:
    """Read labelled fixtures once and expose only those allow-listed resources."""

    def __init__(self, labels_dir: Path) -> None:
        self._entries: list[FixtureEntry] = []
        self._resources: dict[str, Path] = {}
        for filename, model, module in (
            ("quality.json", QualityLabel, "quality"),
            ("bundle_routes.json", RouteLabel, "router"),
            ("notifiable.json", NotifiableLabel, "notifiable"),
        ):
            self._load(labels_dir / filename, model, cast(DemoModule, module))

    def _load(self, path: Path, model: type[LabelT], module: DemoModule) -> None:
        for item in load_labels(path, model):
            resource_path = fixture_path(item)
            resource = json.loads(resource_path.read_text(encoding="utf-8"))
            truth = item.model_dump(mode="json", exclude={"fixture", "source", "difficulty"})
            self._entries.append(
                FixtureEntry(
                    id=item.fixture,
                    name=Path(item.fixture).stem,
                    module=module,
                    resource_type=str(resource["resourceType"]),
                    source=item.source,
                    difficulty=item.difficulty,
                    label=self._label(truth),
                    ground_truth=truth,
                    approved=item.approved_by is not None,
                )
            )
            self._resources[item.fixture] = resource_path

    @staticmethod
    def _label(truth: dict[str, Any]) -> str:
        if "expected_action" in truth:
            low, high = truth["expected_score_range"]
            nik_valid = truth.get("expected_nik_valid")
            nik = " · NIK ✓" if nik_valid is True else " · NIK ✗" if nik_valid is False else ""
            return f"{truth['expected_action']} · {low}–{high}{nik}"
        return str(truth.get("expected_category", truth.get("expected_status", "labelled")))

    def entries(
        self,
        *,
        module: DemoModule | None = None,
        source: Source | None = None,
        difficulty: Difficulty | None = None,
    ) -> list[FixtureEntry]:
        return [
            entry
            for entry in self._entries
            if (module is None or entry.module == module)
            and (source is None or entry.source == source)
            and (difficulty is None or entry.difficulty == difficulty)
        ]

    def get(self, fixture_id: str) -> FixtureEntry | None:
        return next((entry for entry in self._entries if entry.id == fixture_id), None)

    def load_resource(self, fixture_id: str) -> dict[str, Any]:
        path = self._resources.get(fixture_id)
        if path is None:
            raise KeyError(fixture_id)
        return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
