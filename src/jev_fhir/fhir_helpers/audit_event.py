"""Builder for optional FHIR AuditEvent decision records."""

from datetime import datetime

from fhir.resources.R4B.auditevent import AuditEvent


class AuditEventBuilder:
    """Create a minimal valid audit event for a Jev decision."""

    def build(
        self,
        *,
        module_name: str,
        decision: str,
        resource_reference: str,
        timestamp: datetime,
    ) -> dict[str, object]:
        """Build a FHIR R4 AuditEvent without including source clinical content."""
        event: dict[str, object] = {
            "resourceType": "AuditEvent",
            "type": {
                "system": "http://terminology.hl7.org/CodeSystem/audit-event-type",
                "code": "rest",
                "display": "RESTful Operation",
            },
            "recorded": timestamp.isoformat(),
            "agent": [{"who": {"display": f"Jev × FHIR {module_name}"}, "requestor": False}],
            "source": {"observer": {"display": "Jev × FHIR Decision Layer"}},
            "entity": [
                {
                    "what": {"reference": resource_reference},
                    "detail": [{"type": "decision", "valueString": decision}],
                }
            ],
        }
        AuditEvent.parse_obj(event)
        return event
