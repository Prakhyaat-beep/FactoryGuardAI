"""Dataset-bounded telemetry scenarios for the CNC lathe simulator."""

from dataclasses import dataclass
import random

import pandas as pd


TELEMETRY_COLUMNS = {
    "air_temperature": "Air temperature [K]",
    "process_temperature": "Process temperature [K]",
    "rotational_speed": "Rotational speed [rpm]",
    "torque": "Torque [Nm]",
    "tool_wear": "Tool wear [min]",
}
SCENARIOS = {
    "normal": "NORMAL_OPERATION",
    "degradation": "TOOL_DEGRADATION",
    "high_torque": "HIGH_TORQUE",
    "overheating": "OVERHEATING",
    "failure": "FAILURE_SCENARIO",
}


@dataclass(frozen=True)
class TelemetryProfile:
    minimum: dict
    maximum: dict
    median: dict
    q05: dict
    q95: dict

    @classmethod
    def from_dataframe(cls, dataframe):
        missing = set(TELEMETRY_COLUMNS.values()).difference(dataframe.columns)
        if missing:
            raise ValueError(f"Dataset is missing telemetry column(s): {sorted(missing)}")
        columns = list(TELEMETRY_COLUMNS.values())
        return cls(
            minimum=dataframe[columns].min().to_dict(),
            maximum=dataframe[columns].max().to_dict(),
            median=dataframe[columns].median().to_dict(),
            q05=dataframe[columns].quantile(0.05).to_dict(),
            q95=dataframe[columns].quantile(0.95).to_dict(),
        )


class CncLatheSimulator:
    """Generate gradual, empirical-range telemetry; it never predicts a condition."""

    def __init__(self, profile, scenario="normal", machine_type="M", seed=42, initial_state=None):
        if scenario not in SCENARIOS:
            raise ValueError(f"Scenario must be one of: {', '.join(SCENARIOS)}.")
        if machine_type not in {"L", "M", "H"}:
            raise ValueError("Machine type must be L, M, or H.")
        self.profile = profile
        self.scenario = scenario
        self.machine_type = machine_type
        self.random = random.Random(seed)
        self.reading_number = 0
        self.state = {key: float(profile.median[column]) for key, column in TELEMETRY_COLUMNS.items()}
        if initial_state and isinstance(initial_state, dict):
            for k, v in initial_state.items():
                if k in self.state and isinstance(v, (int, float)):
                    self.state[k] = float(v)

    def set_scenario(self, scenario):
        if scenario not in SCENARIOS:
            raise ValueError(f"Scenario must be one of: {', '.join(SCENARIOS)}.")
        self.scenario = scenario

    def next_reading(self):
        """Advance one stateful reading while clamping every signal to dataset bounds."""
        self.reading_number += 1
        targets = self._targets()
        noise = self._noise_scale()
        for key, column in TELEMETRY_COLUMNS.items():
            current = self.state[key]
            target = targets[key]
            drift = (target - current) * self._drift_rate()
            variation = self.random.gauss(0, noise[key])
            self.state[key] = self._clamp(key, current + drift + variation)

        # Tool wear only accumulates during a simulated operating run.
        self.state["tool_wear"] = self._clamp(
            "tool_wear", self.state["tool_wear"] + self._wear_increment()
        )
        return {
            "airTemperature": round(self.state["air_temperature"], 2),
            "processTemperature": round(self.state["process_temperature"], 2),
            "rotationalSpeed": round(self.state["rotational_speed"], 2),
            "torque": round(self.state["torque"], 2),
            "toolWear": round(self.state["tool_wear"], 2),
            "type": self.machine_type,
        }

    def _targets(self):
        median = self._values(self.profile.median)
        q05 = self._values(self.profile.q05)
        q95 = self._values(self.profile.q95)
        if self.scenario == "normal":
            return median
        if self.scenario == "degradation":
            return {**median, "tool_wear": q95["tool_wear"], "torque": q95["torque"], "rotational_speed": q05["rotational_speed"]}
        if self.scenario == "high_torque":
            return {**median, "torque": q95["torque"], "rotational_speed": q05["rotational_speed"]}
        if self.scenario == "overheating":
            return {**median, "air_temperature": q95["air_temperature"], "process_temperature": q95["process_temperature"]}
        return {**q95, "rotational_speed": q05["rotational_speed"]}

    def _values(self, source):
        return {key: float(source[column]) for key, column in TELEMETRY_COLUMNS.items()}

    def _noise_scale(self):
        return {
            "air_temperature": 0.03,
            "process_temperature": 0.03,
            "rotational_speed": 3.0,
            "torque": 0.15,
            "tool_wear": 0.0,
        }

    def _drift_rate(self):
        return 0.03 if self.scenario == "normal" else 0.08

    def _wear_increment(self):
        return self.random.uniform(0.05, 0.2) if self.scenario == "normal" else self.random.uniform(0.45, 1.0)

    def _clamp(self, key, value):
        column = TELEMETRY_COLUMNS[key]
        return min(float(self.profile.maximum[column]), max(float(self.profile.minimum[column]), value))
