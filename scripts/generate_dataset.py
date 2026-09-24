"""Generate the deterministic D0.5 synthetic benchmark corpus."""

from __future__ import annotations

import argparse
import filecmp
import json
import random
import shutil
import tempfile
from pathlib import Path
from typing import Any

from jev_fhir.config import PROJECT_ROOT

DEFAULT_SEED = 42
GIVEN = [
    "Aditya",
    "Agus",
    "Andi",
    "Anisa",
    "Ari",
    "Ayu",
    "Bagus",
    "Bayu",
    "Citra",
    "Dewi",
    "Dimas",
    "Eka",
    "Fajar",
    "Fitri",
    "Galih",
    "Indah",
    "Intan",
    "Joko",
    "Kartika",
    "Lestari",
    "Maya",
    "Nadia",
    "Putra",
    "Rani",
    "Ratna",
    "Rizky",
    "Sari",
    "Siti",
    "Sri",
    "Taufik",
    "Wahyu",
    "Wulan",
    "Yudi",
    "Yuni",
    "Zahra",
    "Bima",
    "Dian",
    "Hana",
    "Ilham",
    "Kiki",
]
FAMILY = [
    "Abdullah",
    "Anwar",
    "Basuki",
    "Cahyadi",
    "Darmawan",
    "Fauzi",
    "Gunawan",
    "Hidayat",
    "Irawan",
    "Kurniawan",
    "Laksana",
    "Maulana",
    "Nugroho",
    "Pratama",
    "Putri",
    "Ramadhan",
    "Santoso",
    "Setiawan",
    "Siregar",
    "Suryani",
    "Susanto",
    "Utami",
    "Wijaya",
    "Wibowo",
    "Yusuf",
    "Zulkarnain",
    "Anggraini",
    "Budiman",
    "Hartono",
    "Iskandar",
    "Jaya",
    "Kusuma",
    "Lubis",
    "Mulyani",
    "Permata",
    "Rahman",
    "Saputra",
    "Sari",
    "Wardani",
    "Yuliana",
]
CITIES = [
    "Jakarta",
    "Bandung",
    "Surabaya",
    "Medan",
    "Makassar",
    "Denpasar",
    "Yogyakarta",
    "Semarang",
]
REGIONS = ["317301", "327301", "357801", "127101", "517101", "347101"]
LOINC = ["718-7", "789-8", "2345-7", "4548-4", "2160-0", "56888-1"]


def write(path: Path, item: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(item, indent=2, sort_keys=True) + "\n")


def patient(i: int, r: random.Random) -> dict[str, Any]:
    female = i % 2 == 0
    birth = f"199{r.randrange(0, 10)}-{r.randrange(1, 13):02d}-{r.randrange(1, 28):02d}"
    y, m, d = map(int, birth.split("-"))
    day = d + (40 if female else 0)
    nik = f"{r.choice(REGIONS)}{day:02d}{m:02d}{y % 100:02d}{r.randrange(1, 10000):04d}"
    return {
        "resourceType": "Patient",
        "id": f"generated-patient-{i:03d}",
        "identifier": [{"system": "nik", "value": nik}],
        "name": [{"family": r.choice(FAMILY), "given": [r.choice(GIVEN)]}],
        "gender": "female" if female else "male",
        "birthDate": birth,
        "telecom": [{"system": "phone", "value": f"+628{r.randrange(100000000, 999999999)}"}],
        "address": [
            {
                "text": f"Jl. Melati No. {r.randrange(1, 200)}, {r.choice(CITIES)}",
                "city": r.choice(CITIES),
                "postalCode": str(r.randrange(10000, 99999)),
                "country": "ID",
            }
        ],
    }


def observation(
    i: int,
    r: random.Random,
    subject: str = "Patient/generated-patient-000",
    encounter: str | None = None,
) -> dict[str, Any]:
    x = {
        "resourceType": "Observation",
        "id": f"generated-observation-{i:03d}",
        "status": "final",
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": r.choice(LOINC),
                    "display": "Laboratory test",
                }
            ]
        },
        "subject": {"reference": subject},
        "valueQuantity": {"value": r.randrange(0, 200), "unit": "mg/dL"},
        "effectiveDateTime": "2026-03-10T08:00:00+07:00",
    }
    if encounter:
        x["encounter"] = {"reference": encounter}
    return x


def encounter(i: int) -> dict[str, Any]:
    return {
        "resourceType": "Encounter",
        "id": f"generated-encounter-{i:03d}",
        "status": "finished",
        "class": {
            "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
            "code": "AMB",
            "display": "ambulatory",
        },
    }


def immunization(i: int) -> dict[str, Any]:
    return {
        "resourceType": "Immunization",
        "id": f"generated-immunization-{i:03d}",
        "status": "completed",
        "vaccineCode": {"text": "Influenza vaccine"},
        "patient": {"reference": "Patient/generated-patient-000"},
        "occurrenceDateTime": "2026-03-10",
    }


def dispense(i: int) -> dict[str, Any]:
    return {
        "resourceType": "MedicationDispense",
        "id": f"generated-dispense-{i:03d}",
        "status": "completed",
        "medicationCodeableConcept": {"text": "Paracetamol 500 mg"},
        "subject": {"reference": "Patient/generated-patient-000"},
    }


def condition(i: int, encounter: str | None = None) -> dict[str, Any]:
    x: dict[str, Any] = {
        "resourceType": "Condition",
        "id": f"generated-condition-{i:03d}",
        "code": {"text": "Follow-up condition"},
        "subject": {"reference": "Patient/generated-patient-000"},
    }
    if encounter:
        x["encounter"] = {"reference": encounter}
    return x


def bundle(i: int, category: str, r: random.Random) -> tuple[dict[str, Any], str]:
    typ = r.choice(["collection", "transaction", "batch"])
    n = r.randrange(10, 31) if category in {"lab_result", "unknown"} else r.randrange(1, 10)
    entries: list[dict[str, Any]] = []
    if category == "lab_result":
        resources = [patient(i, r), encounter(i)] + [
            observation(
                i * 100 + j,
                r,
                f"Patient/generated-patient-{i:03d}",
                f"Encounter/generated-encounter-{i:03d}",
            )
            for j in range(max(1, n - 2))
        ]
    elif category == "encounter_summary":
        resources = [encounter(i)] + [
            condition(i * 10 + j, f"Encounter/generated-encounter-{i:03d}")
            for j in range(max(1, n - 1))
        ]
    elif category == "immunization_report":
        resources = [immunization(i * 10 + j) for j in range(n)]
    elif category == "medication_dispense":
        resources = [dispense(i * 10 + j) for j in range(n)]
    else:
        resources = (
            []
            if i % 3 == 0
            else [patient(i, r)]
            if i % 3 == 1
            else [observation(i * 10 + j, r) for j in range(n // 3)]
            + [immunization(i * 10 + j) for j in range(n // 3)]
            + [dispense(i * 10 + j) for j in range(n - 2 * (n // 3))]
        )
    for j, item in enumerate(resources):
        e = {"fullUrl": f"urn:uuid:generated-{i}-{j}", "resource": item}
        if typ in {"transaction", "batch"}:
            e["request"] = {"method": "POST", "url": item["resourceType"]}
        entries.append(e)
    r.shuffle(entries)
    composition = ", ".join(sorted({x["resource"]["resourceType"] for x in entries})) or "empty"
    return (
        {
            "resourceType": "Bundle",
            "id": f"generated-bundle-{i:03d}",
            "type": typ,
            "entry": entries,
        },
        f"{category} template: {len(entries)} entries ({composition}), {typ}.",
    )


def labels_dir() -> Path:
    return PROJECT_ROOT / "benchmarks/dataset/labels"


def replace_generated(name: str, items: list[dict[str, Any]]) -> None:
    path = labels_dir() / name
    old = json.loads(path.read_text())
    write(path.parent / name, [x for x in old if x["source"] != "generated"] + items)


def generate(out: Path, seed: int) -> None:
    r = random.Random(seed)
    q = []
    routes = []
    for i in range(20):
        x = patient(i, r)
        defects = []
        if i >= 8:
            defect = [
                "placeholder family name '-'",
                "future birthDate 2031-03-02",
                "malformed NIK with letters",
            ][i % 3]
            defects = [defect]
            if "placeholder" in defect:
                x["name"][0]["family"] = "-"
            elif "future" in defect:
                x["birthDate"] = "2031-03-02"
            else:
                x["identifier"][0]["value"] = "31730101019000AB"
        write(out / "patients" / f"generated_{i:03d}.json", x)
        q.append(
            {
                "fixture": f"benchmarks/dataset/generated/patients/generated_{i:03d}.json",
                "source": "generated",
                "difficulty": "easy",
                "rationale": "Injected defects: " + ", ".join(defects)
                if defects
                else "Synthetic complete patient from built-in Indonesian name and address lists.",
                "approved_by": None,
                "resource_type": "Patient",
                "expected_action": "review_needed" if defects else "auto_accept",
                "expected_score_range": [0, 69] if defects else [70, 100],
                "expected_nik_valid": False if "malformed NIK with letters" in defects else None,
            }
        )
    for i in range(10):
        x = observation(i, r)
        defects = []
        if i >= 4:
            defect = [
                "missing value",
                "missing code system",
                "status entered-in-error",
                "future effectiveDateTime",
            ][i % 4]
            defects = [defect]
            if defect == "missing value":
                x.pop("valueQuantity")
            elif defect == "missing code system":
                x["code"]["coding"][0].pop("system")
            elif defect == "status entered-in-error":
                x["status"] = "entered-in-error"
            else:
                x["effectiveDateTime"] = "2031-03-02T08:00:00+07:00"
        write(out / "observations" / f"generated_{i:03d}.json", x)
        q.append(
            {
                "fixture": f"benchmarks/dataset/generated/observations/generated_{i:03d}.json",
                "source": "generated",
                "difficulty": "easy",
                "rationale": "Injected defects: " + ", ".join(defects)
                if defects
                else "Synthetic complete laboratory Observation.",
                "approved_by": None,
                "resource_type": "Observation",
                "expected_action": "review_needed" if defects else "auto_accept",
                "expected_score_range": [0, 69] if defects else [70, 100],
                "expected_nik_valid": None,
            }
        )
    cats = (
        ["lab_result"] * 18
        + ["encounter_summary"] * 18
        + ["immunization_report"] * 16
        + ["medication_dispense"] * 16
        + ["unknown"] * 12
    )
    for i, cat in enumerate(cats):
        x, rationale = bundle(i, cat, r)
        write(out / "bundles" / f"generated_{i:03d}.json", x)
        routes.append(
            {
                "fixture": f"benchmarks/dataset/generated/bundles/generated_{i:03d}.json",
                "source": "generated",
                "difficulty": "easy",
                "rationale": rationale,
                "approved_by": "construction",
                "expected_category": cat,
            }
        )
    if out.resolve() == (PROJECT_ROOT / "benchmarks/dataset/generated").resolve():
        replace_generated("quality.json", q)
        replace_generated("bundle_routes.json", routes)


def same_tree(a: Path, b: Path) -> bool:
    aa = sorted(x.relative_to(a) for x in a.rglob("*.json"))
    bb = sorted(x.relative_to(b) for x in b.rglob("*.json"))
    return aa == bb and all(filecmp.cmp(a / x, b / x, shallow=False) for x in aa)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", type=Path, default=PROJECT_ROOT / "benchmarks/dataset/generated")
    p.add_argument("--check", action="store_true")
    a = p.parse_args()
    if a.check:
        with tempfile.TemporaryDirectory() as d:
            expected = Path(d) / "generated"
            generate(expected, a.seed)
            if not a.out.exists() or not same_tree(expected, a.out):
                raise SystemExit("generated dataset differs; run make dataset")
        print("Generated dataset is deterministic and current.")
        return
    if a.out.exists():
        shutil.rmtree(a.out)
    generate(a.out, a.seed)
    print(f"Wrote deterministic generated dataset to {a.out}")


if __name__ == "__main__":
    main()
