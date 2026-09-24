"""Builder for FHIR Flags raised by notifiable-disease decisions."""

from datetime import date

from fhir.resources.R4B.flag import Flag


class FlagBuilder:
    """Create validated FHIR R4 Flag resources for confirmed detections."""

    def build(
        self,
        *,
        condition_code: str,
        condition_display: str,
        subject_reference: str,
        detection_date: date,
    ) -> dict[str, object]:
        """Build a clinical Flag that links the notification to its patient."""
        flag: dict[str, object] = {
            "resourceType": "Flag",
            "status": "active",
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/flag-category",
                            "code": "clinical",
                        }
                    ]
                }
            ],
            "code": {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": "281269004",
                        "display": "Notifiable disease",
                    }
                ],
                "text": f"{condition_display} ({condition_code}) - mandatory reporting",
            },
            "subject": {"reference": subject_reference},
            "period": {"start": detection_date.isoformat()},
        }
        Flag.parse_obj(flag)
        return flag
