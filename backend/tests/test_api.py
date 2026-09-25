import unittest
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader

from app import create_app
from database import PredictionRepository
from simulator.scenarios import CncLatheSimulator, TelemetryProfile


VALID_PAYLOAD = {
    "airTemperature": 300.0,
    "processTemperature": 310.0,
    "rotationalSpeed": 1500,
    "torque": 40.0,
    "toolWear": 120,
    "type": "M",
}


class FactoryGuardApiTests(unittest.TestCase):
    def setUp(self):
        self.database_path = Path(__file__).resolve().parents[1] / "data" / f"test_fg_{self._testMethodName}.db"
        try:
            self.database_path.unlink(missing_ok=True)
        except PermissionError:
            pass
        app = create_app({"TESTING": True, "DATABASE_PATH": str(self.database_path)})
        self.client = app.test_client()
        self.unauthenticated_client = app.test_client()
        registered = self.client.post("/api/auth/register", json={"username": "admin", "password": "secure-password"})
        self.assertEqual(registered.status_code, 201)
        logged_in = self.client.post("/api/auth/login", json={"username": "admin", "password": "secure-password"})
        self.assertEqual(logged_in.status_code, 200)

    def tearDown(self):
        try:
            self.database_path.unlink(missing_ok=True)
        except PermissionError:
            pass

    def test_health(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")

    def test_valid_login(self):
        self.client.post("/api/auth/logout")
        response = self.client.post("/api/auth/login", json={"username": "admin", "password": "secure-password"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["user"]["role"], "Admin")

    def test_current_user_and_registration_validation(self):
        current_user = self.client.get("/api/auth/me")
        self.assertEqual(current_user.status_code, 200)
        self.assertEqual(current_user.get_json()["user"]["username"], "admin")
        invalid_registration = self.unauthenticated_client.post(
            "/api/auth/register", json={"username": "a", "password": "short"}
        )
        self.assertEqual(invalid_registration.status_code, 400)

    def test_invalid_login(self):
        response = self.unauthenticated_client.post("/api/auth/login", json={"username": "admin", "password": "wrong-password"})
        self.assertEqual(response.status_code, 401)

    def test_protected_endpoint_requires_authentication(self):
        response = self.unauthenticated_client.get("/api/predictions")
        self.assertEqual(response.status_code, 401)

    def test_authenticated_request_and_logout(self):
        self.assertEqual(self.client.get("/api/predictions").status_code, 200)
        self.assertEqual(self.client.post("/api/auth/logout").status_code, 200)
        self.assertEqual(self.client.get("/api/predictions").status_code, 401)

    def test_valid_prediction(self):
        response = self.client.post("/api/predict", json=VALID_PAYLOAD)
        body = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertIn(body["condition"], {"Normal", "Warning", "Critical"})
        self.assertGreaterEqual(body["failureRisk"], 0)
        self.assertLessEqual(body["failureRisk"], 100)
        self.assertIn("machineFailure", body["probabilities"])
        self.assertIn("predictionId", body)

    def test_prediction_history_and_detail(self):
        payload = {**VALID_PAYLOAD, "machineId": "Press-01"}
        created = self.client.post("/api/predict", json=payload).get_json()
        history = self.client.get("/api/predictions")
        self.assertEqual(history.status_code, 200)
        records = history.get_json()["predictions"]
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["machineId"], "Press-01")
        detail = self.client.get(f"/api/predictions/{created['predictionId']}")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.get_json()["id"], created["predictionId"])

    def test_unknown_prediction_returns_404(self):
        response = self.client.get("/api/predictions/999")
        self.assertEqual(response.status_code, 404)

    def test_dashboard_uses_saved_prediction_data(self):
        self.client.post("/api/predict", json={**VALID_PAYLOAD, "machineId": "Line-01"})
        self.client.post("/api/predict", json={**VALID_PAYLOAD, "machineId": "Line-02"})
        summary = self.client.get("/api/dashboard/summary")
        self.assertEqual(summary.status_code, 200)
        body = summary.get_json()
        self.assertEqual(body["totalPredictions"], 2)
        self.assertEqual(sum(body["conditionCounts"].values()), 2)
        self.assertEqual(len(body["recentPredictions"]), 2)
        self.assertEqual(len(body["machineStatuses"]), 2)
        trends = self.client.get("/api/dashboard/trends")
        self.assertEqual(trends.status_code, 200)
        self.assertEqual(len(trends.get_json()["trends"]), 2)

    def test_model_performance_results_are_available(self):
        response = self.client.get("/api/models/performance")
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertIn(body["selected_model"], body["models"])
        self.assertEqual(len(body["models"]), 5)

    def test_maintenance_priority_rules(self):
        from services.maintenance_service import get_maintenance_guidance
        self.assertEqual(get_maintenance_guidance("Normal")["priority"], "Routine")
        self.assertEqual(get_maintenance_guidance("Warning")["priority"], "Planned")
        self.assertEqual(get_maintenance_guidance("Critical")["priority"], "Immediate")

    def test_maintenance_records_and_machine_detail(self):
        prediction = self.client.post("/api/predict", json={**VALID_PAYLOAD, "machineId": "Press-01"})
        self.assertEqual(prediction.status_code, 200)
        payload = {
            "machineId": "Press-01", "maintenanceDate": "2026-09-13",
            "maintenanceType": "Inspection", "issue": "Review model alert",
            "actionTaken": "Checked torque", "notes": "No damage observed",
        }
        created = self.client.post("/api/maintenance", json=payload)
        self.assertEqual(created.status_code, 201)
        history = self.client.get("/api/maintenance?machineId=Press-01").get_json()["maintenanceRecords"]
        self.assertEqual(len(history), 1)
        detail = self.client.get("/api/machines/Press-01")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.get_json()["latestPrediction"]["machineId"], "Press-01")
        self.assertEqual(len(detail.get_json()["maintenanceRecords"]), 1)

    def test_critical_prediction_creates_and_resolves_alert(self):
        critical_payload = {
            "machineId": "Alert-01", "airTemperature": 298.9, "processTemperature": 309.1,
            "rotationalSpeed": 2861, "torque": 4.6, "toolWear": 143, "type": "L",
        }
        created = self.client.post("/api/predict", json=critical_payload)
        self.assertEqual(created.status_code, 200)
        alert_id = created.get_json()["alertId"]
        alerts = self.client.get("/api/alerts").get_json()["alerts"]
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["status"], "Active")
        self.assertEqual(self.client.get("/api/dashboard/summary").get_json()["activeAlertCount"], 1)
        resolved = self.client.patch(f"/api/alerts/{alert_id}", json={"status": "Resolved"})
        self.assertEqual(resolved.status_code, 200)
        self.assertEqual(resolved.get_json()["status"], "Resolved")
        self.assertIsNotNone(resolved.get_json()["resolvedAt"])
        alert_history = self.client.get("/api/alerts").get_json()["alerts"]
        self.assertEqual(alert_history[0]["status"], "Resolved")

    def test_normal_prediction_does_not_create_alert(self):
        self.client.post("/api/predict", json={**VALID_PAYLOAD, "machineId": "Normal-01"})
        self.assertEqual(self.client.get("/api/alerts").get_json()["alerts"], [])

    def test_machine_report_uses_stored_condition_data(self):
        repository = PredictionRepository(self.database_path)
        for condition, risk in (("Normal", 8.0), ("Warning", 45.0), ("Critical", 91.0)):
            machine_id = f"Report-{condition}"
            prediction = {
                "condition": condition,
                "failureRisk": risk,
                "probabilities": {"noFailure": 100 - risk, "machineFailure": risk},
                "recommendation": f"{condition} test recommendation.",
                "riskLabel": "Model-derived risk indicator.",
                "maintenancePriority": {"Normal": "Routine", "Warning": "Planned", "Critical": "Immediate"}[condition],
                "maintenanceDisclaimer": "Decision-support only.",
            }
            repository.create({**VALID_PAYLOAD, "machineId": machine_id}, prediction)
            response = self.client.get(f"/api/machines/{machine_id}/report")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.mimetype, "application/pdf")
            self.assertTrue(response.data.startswith(b"%PDF"))
            report_text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(response.data)).pages)
            self.assertIn(machine_id, report_text)
            self.assertIn(condition, report_text)
            self.assertIn(f"{risk}%", report_text)

    def test_unknown_machine_report_returns_404(self):
        response = self.client.get("/api/machines/Not-Saved/report")
        self.assertEqual(response.status_code, 404)

    def test_missing_field(self):
        payload = VALID_PAYLOAD.copy()
        payload.pop("torque")
        response = self.client.post("/api/predict", json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Missing required field", response.get_json()["error"])

    def test_invalid_field(self):
        payload = VALID_PAYLOAD.copy()
        payload["rotationalSpeed"] = "fast"
        response = self.client.post("/api/predict", json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("must be a numeric", response.get_json()["error"])

    def test_out_of_range_field(self):
        payload = VALID_PAYLOAD.copy()
        payload["rotationalSpeed"] = -50
        response = self.client.post("/api/predict", json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("must be between", response.get_json()["error"])

    def test_invalid_json(self):
        response = self.client.post(
            "/api/predict", data="not valid json", content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("valid JSON", response.get_json()["error"])

    def test_cnc_simulator_generates_stateful_dataset_bounded_readings(self):
        import pandas as pd

        dataframe = pd.DataFrame({
            "Air temperature [K]": [295.3, 300.0, 304.5],
            "Process temperature [K]": [305.7, 310.0, 313.8],
            "Rotational speed [rpm]": [1168, 1538, 2886],
            "Torque [Nm]": [3.8, 40.0, 76.6],
            "Tool wear [min]": [0, 108, 253],
        })
        profile = TelemetryProfile.from_dataframe(dataframe)
        simulator = CncLatheSimulator(profile, scenario="degradation", seed=7)
        first, second = simulator.next_reading(), simulator.next_reading()
        self.assertGreaterEqual(second["toolWear"], first["toolWear"])
        self.assertNotEqual(first, second)
        self.assertTrue(295.3 <= second["airTemperature"] <= 304.5)
        self.assertTrue(305.7 <= second["processTemperature"] <= 313.8)
        self.assertTrue(1168 <= second["rotationalSpeed"] <= 2886)
        self.assertTrue(3.8 <= second["torque"] <= 76.6)
        self.assertTrue(0 <= second["toolWear"] <= 253)

    def test_simulated_telemetry_reuses_prediction_endpoint_and_machine_detail(self):
        from simulator.scenarios import CncLatheSimulator, TelemetryProfile
        import pandas as pd

        dataframe = pd.DataFrame({
            "Air temperature [K]": [299.0, 300.0, 301.0],
            "Process temperature [K]": [309.0, 310.0, 311.0],
            "Rotational speed [rpm]": [1450, 1500, 1550],
            "Torque [Nm]": [35.0, 40.0, 45.0],
            "Tool wear [min]": [100, 110, 120],
        })
        reading = CncLatheSimulator(TelemetryProfile.from_dataframe(dataframe), seed=1).next_reading()
        response = self.client.post("/api/predict", json={"machineId": "CNC-LATHE-01", **reading})
        self.assertEqual(response.status_code, 200)
        detail = self.client.get("/api/machines/CNC-LATHE-01")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.get_json()["latestPrediction"]["inputs"]["toolWear"], reading["toolWear"])


if __name__ == "__main__":
    unittest.main()
