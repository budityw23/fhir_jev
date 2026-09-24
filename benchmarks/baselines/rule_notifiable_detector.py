"""Exact ICD-10 lookup baseline for notifiable-disease detection."""

import json
from pathlib import Path
from typing import Any

from jev_fhir.serializer.condition import ConditionSerializer


def is_notifiable(condition: dict[str, Any], disease_data_path: Path) -> bool:
    """Return true only when the exact serialized ICD-10 code is in the reference data."""
    with disease_data_path.open(encoding="utf-8") as data_file:
        diseases = json.load(data_file)["diseases"]
    codes = {
        code
        for disease in diseases
        if isinstance(disease, dict)
        for code in disease.get("icd10_codes", [])
        if isinstance(code, str)
    }
    code = ConditionSerializer().serialize(condition)["code_value"]
    return isinstance(code, str) and code in codes
