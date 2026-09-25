"""Internal, automated telemetry simulation service for CNC Lathe machines."""

from collections import deque
from datetime import datetime, timezone
from pathlib import Path
import threading
import time

import pandas as pd

from simulator.scenarios import CncLatheSimulator, SCENARIOS, TELEMETRY_COLUMNS, TelemetryProfile
from services.rutl_service import RutlService
from services.seed_service import DEFAULT_FLEET_CONFIGS

DEFAULT_DATASET = Path(__file__).resolve().parents[1] / "data" / "predictive_maintenance.csv"
HEARTBEAT_TIMEOUT_SECONDS = 45.0
DEFAULT_TICK_INTERVAL_SECONDS = 3.0


class MachineSimulation:
    """Maintains independent state, history, and simulation parameters for one CNC machine."""

    def __init__(self, machine_id, simulator, scenario="normal", machine_type="M", interval=DEFAULT_TICK_INTERVAL_SECONDS):
        self.machine_id = machine_id
        self.simulator = simulator
        self.scenario = scenario
        self.machine_type = machine_type
        self.interval = interval
        self.is_active = True
        self.last_heartbeat = time.time()
        self.last_tick = 0.0
        self.latest_telemetry = None
        self.latest_prediction = None
        self.latest_explanation = None
        self.latest_rutl = None
        self.recent_readings = deque(maxlen=20)


class SimulationService:
    """Manages software-based CNC lathe simulation runs directly inside FactoryGuard."""

    def __init__(self, repository, prediction_service, explanation_service, dataset_path=None):
        self.repository = repository
        self.prediction_service = prediction_service
        self.explanation_service = explanation_service
        self.rutl_service = RutlService()
        self.dataset_path = Path(dataset_path) if dataset_path else DEFAULT_DATASET
        self._profile = None
        self._machines = {}
        self._lock = threading.Lock()
        self._worker_thread = None
        self._stop_worker = False

    def _get_profile(self):
        if self._profile is None:
            if not self.dataset_path.is_file():
                raise FileNotFoundError(f"Simulation dataset not found at {self.dataset_path}")
            df = pd.read_csv(self.dataset_path)
            self._profile = TelemetryProfile.from_dataframe(df)
        return self._profile

    def start_background_worker(self):
        """Start a single centralized daemon thread to tick active simulations."""
        with self._lock:
            if self._worker_thread is not None and self._worker_thread.is_alive():
                return
            self._stop_worker = False
            self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True, name="FactoryGuard-SimulatorWorker")
            self._worker_thread.start()

    def _worker_loop(self):
        while not self._stop_worker:
            now = time.time()
            to_tick = []
            with self._lock:
                for machine_id, machine in self._machines.items():
                    # Stop simulation if client has not polled within heartbeat timeout
                    if now - machine.last_heartbeat > HEARTBEAT_TIMEOUT_SECONDS:
                        machine.is_active = False
                        continue
                    if machine.is_active and (now - machine.last_tick >= machine.interval):
                        to_tick.append(machine_id)

            for machine_id in to_tick:
                try:
                    self._tick_machine(machine_id)
                except Exception:
                    pass

            time.sleep(0.5)

    def _tick_machine(self, machine_id):
        with self._lock:
            machine = self._machines.get(machine_id)
            if machine is None or not machine.is_active:
                return None

        # 1. Advance simulator telemetry (never generates Target or Failure Type)
        reading = machine.simulator.next_reading()
        telemetry_payload = {"machineId": machine_id, **reading}

        # 2. Feed telemetry into existing ML prediction pipeline
        prediction = self.prediction_service.predict(telemetry_payload)
        prediction["timestamp"] = datetime.now(timezone.utc).isoformat()

        # 3. Persist prediction in SQLite
        prediction_id = self.repository.create(telemetry_payload, prediction)
        prediction["id"] = prediction_id
        prediction["predictionId"] = prediction_id

        # 4. Evaluate automated alert
        alert_id = self.repository.create_alert_if_needed(telemetry_payload, prediction)
        if alert_id is not None:
            prediction["alertId"] = alert_id

        # 5. Generate transparent model explanation
        explanation = self.explanation_service.explain(telemetry_payload, prediction)

        # 6. Estimate Remaining Useful Tool Life (RUTL)
        rutl = self.rutl_service.estimate(reading["toolWear"], list(machine.recent_readings))

        # 7. Store latest in memory
        with self._lock:
            machine.latest_telemetry = telemetry_payload
            machine.latest_prediction = prediction
            machine.latest_explanation = explanation
            machine.latest_rutl = rutl
            machine.last_tick = time.time()
            machine.recent_readings.append({
                "timestamp": prediction["timestamp"],
                "airTemperature": reading["airTemperature"],
                "processTemperature": reading["processTemperature"],
                "rotationalSpeed": reading["rotationalSpeed"],
                "torque": reading["torque"],
                "toolWear": reading["toolWear"],
                "remainingLife": rutl["remaining_tool_life"],
                "failureRisk": prediction["failureRisk"],
                "condition": prediction["condition"],
            })
            return machine

    def update_machine_state_from_prediction(self, machine_id, payload, prediction, explanation=None):
        """Associate prediction telemetry with machine, update/resume simulation state, and continue stream."""
        input_state = {
            "air_temperature": float(payload["airTemperature"]),
            "process_temperature": float(payload["processTemperature"]),
            "rotational_speed": float(payload["rotationalSpeed"]),
            "torque": float(payload["torque"]),
            "tool_wear": float(payload["toolWear"]),
        }
        machine_type = payload.get("type", "M")
        now = time.time()

        with self._lock:
            machine = self._machines.get(machine_id)
            if machine is None:
                simulator = CncLatheSimulator(
                    self._get_profile(),
                    scenario="normal",
                    machine_type=machine_type,
                    seed=hash(machine_id) % 10000,
                    initial_state=input_state,
                )
                machine = MachineSimulation(
                    machine_id=machine_id,
                    simulator=simulator,
                    scenario="normal",
                    machine_type=machine_type,
                )
                self._machines[machine_id] = machine
            else:
                for key, val in input_state.items():
                    machine.simulator.state[key] = val
                machine.simulator.machine_type = machine_type

            telemetry_payload = {"machineId": machine_id, **payload}
            rutl = self.rutl_service.estimate(payload["toolWear"], list(machine.recent_readings))

            machine.is_active = True
            machine.last_heartbeat = now
            machine.last_tick = now
            machine.latest_telemetry = telemetry_payload
            machine.latest_prediction = prediction
            machine.latest_explanation = explanation
            machine.latest_rutl = rutl
            machine.recent_readings.append({
                "timestamp": prediction.get("timestamp", datetime.now(timezone.utc).isoformat()),
                "airTemperature": payload["airTemperature"],
                "processTemperature": payload["processTemperature"],
                "rotationalSpeed": payload["rotationalSpeed"],
                "torque": payload["torque"],
                "toolWear": payload["toolWear"],
                "remainingLife": rutl["remaining_tool_life"],
                "failureRisk": prediction["failureRisk"],
                "condition": prediction["condition"],
            })

        self.start_background_worker()
        return machine

    def start_or_resume(self, machine_id, scenario="normal", machine_type="M"):
        """Initialize or resume simulation for a machine when opened by a user."""
        self.start_background_worker()
        now = time.time()

        fleet_map = {cfg["machineId"]: cfg for cfg in DEFAULT_FLEET_CONFIGS}
        if scenario == "normal" and machine_id in fleet_map:
            scenario = fleet_map[machine_id].get("scenario", "normal")

        with self._lock:
            machine = self._machines.get(machine_id)
            if machine is None:
                # Attempt to restore state from SQLite to preserve accumulated wear & sensors
                initial_state = None
                saved_detail = self.repository.machine_detail(machine_id)
                if saved_detail and saved_detail.get("latestPrediction"):
                    inputs = saved_detail["latestPrediction"].get("inputs", {})
                    initial_state = {
                        "air_temperature": float(inputs.get("airTemperature", 300.0)),
                        "process_temperature": float(inputs.get("processTemperature", 310.0)),
                        "rotational_speed": float(inputs.get("rotationalSpeed", 1500.0)),
                        "torque": float(inputs.get("torque", 40.0)),
                        "tool_wear": float(inputs.get("toolWear", 0.0)),
                    }
                    machine_type = inputs.get("type", machine_type)

                simulator = CncLatheSimulator(
                    self._get_profile(),
                    scenario=scenario,
                    machine_type=machine_type,
                    seed=hash(machine_id) % 10000,
                    initial_state=initial_state,
                )
                machine = MachineSimulation(
                    machine_id=machine_id,
                    simulator=simulator,
                    scenario=scenario,
                    machine_type=machine_type,
                )
                self._machines[machine_id] = machine
            else:
                machine.is_active = True
                if scenario and scenario in SCENARIOS and machine.scenario != scenario:
                    machine.scenario = scenario
                    machine.simulator.set_scenario(scenario)

            machine.last_heartbeat = now

        # If no reading exists yet, perform immediate synchronous tick
        if machine.latest_telemetry is None:
            self._tick_machine(machine_id)

        return self.get_machine_status(machine_id)

    def set_scenario(self, machine_id, scenario):
        """Update the operational scenario for a machine (affects physics/drift, NOT predictions directly)."""
        if scenario not in SCENARIOS:
            raise ValueError(f"Scenario must be one of: {', '.join(SCENARIOS)}")
        with self._lock:
            machine = self._machines.get(machine_id)
            if machine:
                machine.scenario = scenario
                machine.simulator.set_scenario(scenario)
                machine.last_heartbeat = time.time()
                machine.is_active = True
        return self.get_machine_status(machine_id)

    def stop_machine(self, machine_id):
        """Pause simulation for a machine."""
        with self._lock:
            machine = self._machines.get(machine_id)
            if machine:
                machine.is_active = False
        return self.get_machine_status(machine_id)

    def get_machine_status(self, machine_id):
        """Fetch live telemetry, model prediction, XAI explanation, and trends."""
        with self._lock:
            machine = self._machines.get(machine_id)
            if machine:
                machine.last_heartbeat = time.time()
                machine.is_active = True

        # If machine was not loaded in memory, try starting it
        if machine is None:
            return self.start_or_resume(machine_id)

        # If stale (more than interval elapsed since last tick), tick once
        if time.time() - machine.last_tick > machine.interval:
            self._tick_machine(machine_id)

        with self._lock:
            # Get active alerts for this machine
            all_alerts = self.repository.list_alerts()
            machine_alerts = [a for a in all_alerts if a.get("machineId") == machine_id and a.get("status") == "Active"]

            rutl = machine.latest_rutl
            if rutl is None and machine.latest_telemetry:
                rutl = self.rutl_service.estimate(machine.latest_telemetry.get("toolWear", 0), list(machine.recent_readings))

            return {
                "machineId": machine.machine_id,
                "status": "ONLINE" if machine.is_active else "STANDBY",
                "scenario": machine.scenario,
                "scenarioDescription": SCENARIOS.get(machine.scenario, machine.scenario),
                "type": machine.machine_type,
                "intervalSeconds": machine.interval,
                "lastUpdated": machine.latest_prediction.get("timestamp") if machine.latest_prediction else None,
                "telemetry": machine.latest_telemetry,
                "prediction": machine.latest_prediction,
                "explanation": machine.latest_explanation,
                "rutl": rutl,
                "recentTrend": list(machine.recent_readings),
                "activeAlerts": machine_alerts,
            }
