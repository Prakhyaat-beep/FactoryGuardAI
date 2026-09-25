"""Validation and inference logic for machine-failure predictions."""

import math

import pandas as pd

from ml.predict import load_trained_model
from ml.preprocess import CATEGORICAL_FEATURES, NUMERIC_FEATURES
from services.maintenance_service import get_maintenance_guidance


API_TO_MODEL_FEATURES = {
    "airTemperature": "Air temperature [K]",
    "processTemperature": "Process temperature [K]",
    "rotationalSpeed": "Rotational speed [rpm]",
    "torque": "Torque [Nm]",
    "toolWear": "Tool wear [min]",
    "type": "Type",
}

# Bounds check clearly invalid sensor entries; they are not model-calibration limits.
NUMERIC_BOUNDS = {
    "airTemperature": (250, 400),
    "processTemperature": (250, 450),
    "rotationalSpeed": (1, 20000),
    "torque": (0, 1000),
    "toolWear": (0, 10000),
}
VALID_TYPES = {"L", "M", "H"}


class ValidationError(ValueError):
    """Raised when a client prediction request is invalid."""


class ModelUnavailableError(RuntimeError):
    """Raised when the saved model cannot be loaded."""


class PredictionService:
    """Turn validated API payloads into model predictions."""

    def __init__(self, normal_max_percent, warning_max_percent):
        if not 0 <= normal_max_percent < warning_max_percent <= 100:
            raise ValueError("Risk thresholds must satisfy 0 <= normal < warning <= 100.")
        self.normal_max_percent = normal_max_percent
        self.warning_max_percent = warning_max_percent
        self._model = None

    def _get_model(self):
        if self._model is None:
            try:
                self._model = load_trained_model()
            except (FileNotFoundError, OSError, ValueError) as error:
                raise ModelUnavailableError from error
        return self._model

    def _validate_payload(self, payload):
        if not isinstance(payload, dict):
            raise ValidationError("JSON body must be an object containing machine parameters.")

        missing_fields = [field for field in API_TO_MODEL_FEATURES if field not in payload]
        if missing_fields:
            raise ValidationError(f"Missing required field(s): {', '.join(missing_fields)}.")

        machine_id = payload.get("machineId")
        if machine_id is not None and (
            not isinstance(machine_id, str) or not machine_id.strip() or len(machine_id) > 100
        ):
            raise ValidationError("'machineId' must be a non-empty text value up to 100 characters.")

        validated = {}
        for api_name, (minimum, maximum) in NUMERIC_BOUNDS.items():
            value = payload[api_name]
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValidationError(f"'{api_name}' must be a numeric value.")
            if not math.isfinite(value) or not minimum <= value <= maximum:
                raise ValidationError(
                    f"'{api_name}' must be between {minimum} and {maximum}."
                )
            validated[API_TO_MODEL_FEATURES[api_name]] = float(value)

        machine_type = payload["type"]
        if not isinstance(machine_type, str) or machine_type.upper() not in VALID_TYPES:
            raise ValidationError("'type' must be one of: L, M, H.")
        validated[API_TO_MODEL_FEATURES["type"]] = machine_type.upper()
        return validated

    def _condition_and_recommendation(self, failure_risk):
        if failure_risk < self.normal_max_percent:
            return "Normal", "Continue routine monitoring and scheduled maintenance."
        if failure_risk < self.warning_max_percent:
            return "Warning", "Inspect machine parameters and schedule preventive maintenance."
        return "Critical", "Inspect the machine promptly and plan maintenance before continued operation."

    def predict(self, payload):
        """Validate an API payload and return a model-derived failure-risk response."""
        validated = self._validate_payload(payload)
        feature_order = NUMERIC_FEATURES + CATEGORICAL_FEATURES
        feature_frame = pd.DataFrame([validated], columns=feature_order)
        model = self._get_model()

        probabilities = model.predict_proba(feature_frame)[0]
        class_probabilities = dict(zip(model.classes_, probabilities))
        failure_risk = round(float(class_probabilities.get(1, 0.0)) * 100, 2)
        normal_probability = round(float(class_probabilities.get(0, 0.0)) * 100, 2)
        condition, _ = self._condition_and_recommendation(failure_risk)
        guidance = get_maintenance_guidance(condition)

        return {
            "condition": condition,
            "failureRisk": failure_risk,
            "riskLabel": "model-derived failure score, not a calibrated industrial probability",
            "probabilities": {
                "noFailure": normal_probability,
                "machineFailure": failure_risk,
            },
            "recommendation": guidance["recommendation"],
            "maintenancePriority": guidance["priority"],
            "maintenanceDisclaimer": "Decision-support suggestion only; it does not guarantee machine failure.",
        }
