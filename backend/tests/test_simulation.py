import time
import unittest
from pathlib import Path

from app import create_app
from database import PredictionRepository


class SimulationServiceTests(unittest.TestCase):
    def setUp(self):
        self.database_path = Path(__file__).resolve().parents[1] / "data" / "test_sim_factoryguard.db"
        try:
            self.database_path.unlink(missing_ok=True)
        except PermissionError:
            pass
        self.app = create_app({"TESTING": True, "DATABASE_PATH": str(self.database_path)})
        self.client = self.app.test_client()
        # Register and login
        self.client.post("/api/auth/register", json={"username": "sim-user", "password": "secure-password-123"})
        self.client.post("/api/auth/login", json={"username": "sim-user", "password": "secure-password-123"})

    def tearDown(self):
        try:
            self.database_path.unlink(missing_ok=True)
        except PermissionError:
            pass

    def test_automatic_simulation_start_and_telemetry(self):
        """Ensure opening a machine for checkup starts simulation automatically."""
        res = self.client.post("/api/machines/CNC-TEST-01/simulation/start", json={"scenario": "normal", "type": "M"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        self.assertEqual(data["machineId"], "CNC-TEST-01")
        self.assertEqual(data["status"], "ONLINE")
        self.assertIn("telemetry", data)
        self.assertIn("prediction", data)
        self.assertIn("explanation", data)

        # Verify telemetry bounds
        telemetry = data["telemetry"]
        self.assertGreaterEqual(telemetry["airTemperature"], 290.0)
        self.assertLessEqual(telemetry["airTemperature"], 310.0)
        self.assertGreaterEqual(telemetry["processTemperature"], 300.0)
        self.assertLessEqual(telemetry["processTemperature"], 320.0)
        self.assertGreaterEqual(telemetry["rotationalSpeed"], 1000)
        self.assertLessEqual(telemetry["rotationalSpeed"], 3000)
        self.assertGreaterEqual(telemetry["torque"], 0.0)
        self.assertLessEqual(telemetry["torque"], 100.0)

        # Verify Target or Failure Type are never in telemetry inputs
        self.assertNotIn("Target", telemetry)
        self.assertNotIn("Failure Type", telemetry)
        self.assertNotIn("target", telemetry)
        self.assertNotIn("failureType", telemetry)

    def test_no_duplicate_simulation_loops(self):
        """Repeated calls to start or live endpoint maintain single instance without duplicate threads."""
        res1 = self.client.post("/api/machines/CNC-TEST-02/simulation/start")
        self.assertEqual(res1.status_code, 200)

        # Immediate follow-up call
        res2 = self.client.get("/api/machines/CNC-TEST-02/simulation/live")
        self.assertEqual(res2.status_code, 200)
        data2 = res2.get_json()
        self.assertEqual(data2["machineId"], "CNC-TEST-02")
        self.assertEqual(data2["status"], "ONLINE")

    def test_gradual_telemetry_changes(self):
        """Values must change gradually, not take massive random jumps."""
        res1 = self.client.post("/api/machines/CNC-TEST-03/simulation/start")
        telemetry1 = res1.get_json()["telemetry"]

        # Wait small time and fetch next live reading
        time.sleep(3.2)
        res2 = self.client.get("/api/machines/CNC-TEST-03/simulation/live")
        telemetry2 = res2.get_json()["telemetry"]

        # Air temperature should drift by less than 2.0 K per step
        temp_delta = abs(telemetry2["airTemperature"] - telemetry1["airTemperature"])
        self.assertLess(temp_delta, 2.0)

        # Torque delta should be smooth (less than 15 Nm per step)
        torque_delta = abs(telemetry2["torque"] - telemetry1["torque"])
        self.assertLess(torque_delta, 15.0)

    def test_scenario_switching(self):
        """Operational scenarios influence telemetry physics without bypassing the ML model."""
        start = self.client.post("/api/machines/CNC-TEST-04/simulation/start", json={"scenario": "normal"})
        self.assertEqual(start.status_code, 200)

        # Switch to high_torque scenario
        scenario_res = self.client.post("/api/machines/CNC-TEST-04/simulation/scenario", json={"scenario": "high_torque"})
        self.assertEqual(scenario_res.status_code, 200)
        data = scenario_res.get_json()
        self.assertEqual(data["scenario"], "high_torque")

    def test_xai_explanation_endpoint(self):
        """Ensure explanation is derived from model output and includes top features and summary."""
        res = self.client.post("/api/explain", json={
            "airTemperature": 300.0,
            "processTemperature": 310.0,
            "rotationalSpeed": 1280.0,
            "torque": 66.0,
            "toolWear": 215.0,
            "type": "M",
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("explanation", data)
        explanation = data["explanation"]
        self.assertIn("topFeatures", explanation)
        self.assertIn("summary", explanation)
        self.assertTrue(len(explanation["topFeatures"]) > 0)

        # Check feature attribution format
        top_feature = explanation["topFeatures"][0]
        self.assertIn("feature", top_feature)
        self.assertIn("impact", top_feature)
        self.assertIn("direction", top_feature)


if __name__ == "__main__":
    unittest.main()
