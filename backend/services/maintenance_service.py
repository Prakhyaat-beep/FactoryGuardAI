"""Deterministic maintenance guidance and maintenance-record validation."""

from datetime import date


MAINTENANCE_GUIDANCE = {
    "Normal": {
        "priority": "Routine",
        "recommendation": "Continue normal monitoring and scheduled maintenance.",
    },
    "Warning": {
        "priority": "Planned",
        "recommendation": "Schedule an inspection and preventive maintenance review.",
    },
    "Critical": {
        "priority": "Immediate",
        "recommendation": "Arrange prompt inspection before continued operation.",
    },
}
MAINTENANCE_TYPES = {"Inspection", "Preventive", "Corrective"}


class MaintenanceValidationError(ValueError):
    """Raised when a maintenance record payload is invalid."""


def get_maintenance_guidance(condition):
    """Map a condition to a fixed, explainable maintenance priority and action."""
    return MAINTENANCE_GUIDANCE[condition]


def validate_maintenance_record(payload):
    """Validate only the fixed fields accepted for a maintenance history entry."""
    if not isinstance(payload, dict):
        raise MaintenanceValidationError("JSON body must be a maintenance record object.")
    required = ["machineId", "maintenanceDate", "maintenanceType", "issue"]
    missing = [field for field in required if not payload.get(field)]
    if missing:
        raise MaintenanceValidationError(f"Missing required field(s): {', '.join(missing)}.")
    if not isinstance(payload["machineId"], str) or len(payload["machineId"].strip()) > 100:
        raise MaintenanceValidationError("'machineId' must be text up to 100 characters.")
    try:
        date.fromisoformat(payload["maintenanceDate"])
    except (TypeError, ValueError) as error:
        raise MaintenanceValidationError("'maintenanceDate' must use YYYY-MM-DD format.") from error
    if payload["maintenanceType"] not in MAINTENANCE_TYPES:
        raise MaintenanceValidationError("'maintenanceType' must be Inspection, Preventive, or Corrective.")
    for field, limit in {"issue": 500, "actionTaken": 500, "notes": 1000}.items():
        value = payload.get(field, "")
        if not isinstance(value, str) or len(value) > limit:
            raise MaintenanceValidationError(f"'{field}' must be text up to {limit} characters.")
    return {
        "machineId": payload["machineId"].strip(),
        "maintenanceDate": payload["maintenanceDate"],
        "maintenanceType": payload["maintenanceType"],
        "issue": payload["issue"].strip(),
        "actionTaken": payload.get("actionTaken", "").strip(),
        "notes": payload.get("notes", "").strip(),
    }
