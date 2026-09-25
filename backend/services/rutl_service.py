"""Remaining Useful Tool Life (RUTL) degradation-based estimation service."""

from typing import Any, Dict, List, Optional
import numpy as np

# In the AI4I 2020 dataset, Tool Wear Failure (TWF) occurs strictly between 198 and 253 minutes
# with a mean of 216.56 min and median of 215.0 min. 220.0 min is the standard replacement threshold.
DOCUMENTED_EOL_THRESHOLD_MINUTES = 220.0
NOMINAL_BASELINE_WEAR_RATE = 0.12  # Normal cutting wear increment per simulated cycle


class RutlService:
    """Degradation-based Remaining Useful Tool Life (RUTL) estimator.

    Uses empirical wear thresholds derived from the AI4I 2020 predictive maintenance dataset,
    calculating wear rate from recent historical machine readings and smoothing increments.
    """

    def __init__(self, eol_threshold: float = DOCUMENTED_EOL_THRESHOLD_MINUTES):
        self.eol_threshold = float(eol_threshold)

    def estimate(
        self, current_tool_wear: float, recent_readings: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Calculate degradation-based Remaining Useful Tool Life without fabricating supervised RUL."""
        try:
            current_wear = max(0.0, float(current_tool_wear))
        except (ValueError, TypeError):
            current_wear = 0.0

        remaining_wear = max(0.0, round(self.eol_threshold - current_wear, 2))
        life_percent = max(0.0, min(100.0, round((remaining_wear / self.eol_threshold) * 100, 1)))

        wear_rate, confidence, sample_count = self._estimate_wear_rate(recent_readings, current_wear)

        if remaining_wear <= 0.0:
            estimated_remaining_minutes = 0.0
            remaining_tool_life = 0.0
        elif wear_rate > 0.001:
            estimated_remaining_minutes = round(remaining_wear / wear_rate, 1)
            remaining_tool_life = round(remaining_wear, 2)
        else:
            estimated_remaining_minutes = 0.0
            remaining_tool_life = round(remaining_wear, 2)

        condition, recommendation = self._classify_condition(current_wear, life_percent)

        return {
            "current_tool_wear": round(current_wear, 2),
            "end_of_life_threshold": self.eol_threshold,
            "wear_rate": round(wear_rate, 4),
            "wear_rate_unit": "min/cycle",
            "remaining_tool_life": remaining_tool_life,
            "remaining_tool_life_percent": life_percent,
            "estimated_remaining_minutes": estimated_remaining_minutes,
            "tool_condition": condition,
            "recommendation": recommendation,
            "confidence": confidence,
            "sample_depth": sample_count,
            "method": "degradation_based_estimation",
            "basis": f"Empirical AI4I TWF limit ({self.eol_threshold} min)",
        }

    def _estimate_wear_rate(
        self, recent_readings: Optional[List[Dict[str, Any]]], current_wear: float
    ) -> tuple[float, str, int]:
        if not recent_readings or len(recent_readings) < 2:
            return NOMINAL_BASELINE_WEAR_RATE, "Preliminary (insufficient history)", len(recent_readings) if recent_readings else 0

        # Extract sequential wear values
        wears = []
        for r in recent_readings:
            val = r.get("toolWear")
            if val is not None:
                try:
                    wears.append(float(val))
                except (ValueError, TypeError):
                    pass

        if not wears or len(wears) < 2:
            return NOMINAL_BASELINE_WEAR_RATE, "Preliminary (insufficient history)", len(wears)

        deltas = [wears[i] - wears[i - 1] for i in range(1, len(wears))]
        pos_deltas = [d for d in deltas if d >= 0]

        if not pos_deltas:
            return NOMINAL_BASELINE_WEAR_RATE, "Preliminary (zero wear gradient)", len(wears)

        # Weight recent deltas slightly more to capture acceleration during degradation
        weights = np.linspace(0.8, 1.2, len(pos_deltas))
        weighted_rate = float(np.average(pos_deltas, weights=weights))
        smoothed_rate = max(0.01, round(weighted_rate, 4))

        confidence = "High (linear degradation trajectory)" if len(pos_deltas) >= 5 else "Moderate (accumulating telemetry)"
        return smoothed_rate, confidence, len(pos_deltas)

    def _classify_condition(self, current_wear: float, life_percent: float) -> tuple[str, str]:
        if current_wear >= self.eol_threshold or life_percent <= 0:
            return "Critical - End of Life", "Tool wear exceeds safe limit (220 min). Immediate tool replacement required."
        if current_wear >= 195.0 or life_percent < 15.0:
            return "Degrading", "Tool entering critical wear zone (195–220 min). Schedule tool replacement soon."
        if current_wear >= 140.0 or life_percent < 40.0:
            return "Moderate Wear", "Normal operational wear accumulation. Plan inspection during next tool changeover."
        return "Good", "Tool condition nominal. Cutting edge within standard operating tolerances."
