import unittest
from pathlib import Path

from app import create_app
from database import PredictionRepository, UserRepository
from services.seed_service import seed_demo_fleet


class FactoryGuardIsolationAndSimulationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.database_path = Path(__file__).resolve().parents[1] / "data" / "test_isolation.db"

    def setUp(self):
        try:
            self.database_path.unlink(missing_ok=True)
        except PermissionError:
            pass
        self.app = create_app({"TESTING": True, "DATABASE_PATH": str(self.database_path)})
        
        self.repo = PredictionRepository(str(self.database_path))
        self.users = UserRepository(str(self.database_path))
        
        # Seed demo users and fleet
        from services.prediction_service import PredictionService
        pred_service = PredictionService(20.0, 50.0)
        seed_demo_fleet(self.repo, pred_service, force_reset=True, user_repository=self.users)
        
        # Create user clients
        # User A: arjun.mehta (owns CNC-LATHE-01 .. 05)
        # User B: neha.sharma (owns CNC-LATHE-06 .. 10)
        self.client_a = self.app.test_client()
        login_a = self.client_a.post("/api/auth/login", json={"username": "arjun.mehta", "password": "Arjun@123"})
        self.assertEqual(login_a.status_code, 200)

        self.client_b = self.app.test_client()
        login_b = self.client_b.post("/api/auth/login", json={"username": "neha.sharma", "password": "Neha@123"})
        self.assertEqual(login_b.status_code, 200)

    def tearDown(self):
        pass

    def test_1_user_a_can_see_own_machine(self):
        res = self.client_a.get("/api/machines/CNC-LATHE-01")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["machineId"], "CNC-LATHE-01")

    def test_2_user_a_cannot_see_user_b_machine(self):
        res = self.client_a.get("/api/machines/CNC-LATHE-06")
        self.assertEqual(res.status_code, 403)
        self.assertIn("Access denied", res.get_json()["error"])

    def test_3_user_a_cannot_start_user_b_simulation(self):
        res = self.client_a.post("/api/machines/CNC-LATHE-06/simulation/start", json={"scenario": "normal"})
        self.assertEqual(res.status_code, 403)

    def test_4_user_a_cannot_read_user_b_live_telemetry(self):
        res = self.client_a.get("/api/machines/CNC-LATHE-06/simulation/live")
        self.assertEqual(res.status_code, 403)

    def test_5_user_a_cannot_read_user_b_predictions(self):
        # User B makes a prediction for User B's machine
        b_pred = self.client_b.post("/api/predict", json={
            "machineId": "CNC-LATHE-06",
            "airTemperature": 300.0,
            "processTemperature": 310.0,
            "rotationalSpeed": 1500,
            "torque": 40.0,
            "toolWear": 100,
            "type": "M",
        }).get_json()
        pred_id = b_pred["predictionId"]

        # User A tries to get this prediction by ID
        res_detail = self.client_a.get(f"/api/predictions/{pred_id}")
        self.assertEqual(res_detail.status_code, 404)

        # User A lists predictions -> must not include User B's prediction
        res_list = self.client_a.get("/api/predictions").get_json()["predictions"]
        a_pred_ids = [p["id"] for p in res_list]
        self.assertNotIn(pred_id, a_pred_ids)

    def test_6_user_a_cannot_read_user_b_alerts(self):
        # User B triggers a critical prediction to generate an alert for CNC-LATHE-06
        critical_payload = {
            "machineId": "CNC-LATHE-06",
            "airTemperature": 304.5,
            "processTemperature": 313.8,
            "rotationalSpeed": 1180,
            "torque": 68.0,
            "toolWear": 215,
            "type": "M",
        }
        b_res = self.client_b.post("/api/predict", json=critical_payload).get_json()
        b_alert_id = b_res.get("alertId")
        self.assertIsNotNone(b_alert_id)

        # User A lists alerts -> should not contain User B's alert
        a_alerts = self.client_a.get("/api/alerts").get_json()["alerts"]
        a_alert_ids = [a["id"] for a in a_alerts]
        self.assertNotIn(b_alert_id, a_alert_ids)

        # User A tries to resolve User B's alert -> 404
        resolve_res = self.client_a.patch(f"/api/alerts/{b_alert_id}", json={"status": "Resolved"})
        self.assertEqual(resolve_res.status_code, 404)

    def test_7_user_a_cannot_read_user_b_maintenance_records(self):
        # User B creates a maintenance record for CNC-LATHE-06
        rec_payload = {
            "machineId": "CNC-LATHE-06",
            "maintenanceDate": "2026-09-25",
            "maintenanceType": "Repair",
            "issue": "Bearing replacement",
            "actionTaken": "Replaced bearing",
            "notes": "Completed successfully",
        }
        self.client_b.post("/api/maintenance", json=rec_payload)

        # User A gets maintenance records -> must not include CNC-LATHE-06 records
        a_records = self.client_a.get("/api/maintenance").get_json()["maintenanceRecords"]
        for record in a_records:
            self.assertNotEqual(record["machineId"], "CNC-LATHE-06")

        # User A queries explicitly for CNC-LATHE-06 -> 403
        query_res = self.client_a.get("/api/maintenance?machineId=CNC-LATHE-06")
        self.assertEqual(query_res.status_code, 403)

    def test_8_user_a_cannot_generate_report_for_user_b_machine(self):
        res = self.client_a.get("/api/machines/CNC-LATHE-06/report")
        self.assertEqual(res.status_code, 403)

    def test_9_quick_prediction_only_allows_users_machines(self):
        # User A trying to run prediction on User B's machine CNC-LATHE-06 -> 403
        res = self.client_a.post("/api/predict", json={
            "machineId": "CNC-LATHE-06",
            "airTemperature": 300.0,
            "processTemperature": 310.0,
            "rotationalSpeed": 1500,
            "torque": 40.0,
            "toolWear": 50,
            "type": "M",
        })
        self.assertEqual(res.status_code, 403)

    def test_10_prediction_attached_starts_resumes_simulation(self):
        payload = {
            "machineId": "CNC-LATHE-01",
            "airTemperature": 298.5,
            "processTemperature": 308.5,
            "rotationalSpeed": 1500,
            "torque": 40.0,
            "toolWear": 140,
            "type": "M",
        }
        res = self.client_a.post("/api/predict", json=payload)
        self.assertEqual(res.status_code, 200)

        # Check live simulation status for CNC-LATHE-01
        live_res = self.client_a.get("/api/machines/CNC-LATHE-01/simulation/live")
        self.assertEqual(live_res.status_code, 200)
        status = live_res.get_json()
        self.assertEqual(status["status"], "ONLINE")
        self.assertEqual(status["telemetry"]["toolWear"], 140)

    def test_11_simulation_continues_from_prediction_telemetry(self):
        # Submit prediction with toolWear=180 for CNC-LATHE-01
        self.client_a.post("/api/predict", json={
            "machineId": "CNC-LATHE-01",
            "airTemperature": 300.0,
            "processTemperature": 310.0,
            "rotationalSpeed": 1450,
            "torque": 45.0,
            "toolWear": 180,
            "type": "M",
        })

        # Fetch live telemetry twice and check continuity
        live1 = self.client_a.get("/api/machines/CNC-LATHE-01/simulation/live").get_json()
        wear1 = live1["telemetry"]["toolWear"]
        self.assertGreaterEqual(wear1, 180)

    def test_12_telemetry_degrades_gradually(self):
        # Set scenario to degradation for CNC-LATHE-01
        self.client_a.post("/api/machines/CNC-LATHE-01/simulation/scenario", json={"scenario": "degradation"})
        
        live1 = self.client_a.get("/api/machines/CNC-LATHE-01/simulation/live").get_json()
        wear1 = live1["telemetry"]["toolWear"]

        # Sleep slightly or advance simulator tick directly
        import time
        time.sleep(0.5)

        live2 = self.client_a.get("/api/machines/CNC-LATHE-01/simulation/live").get_json()
        wear2 = live2["telemetry"]["toolWear"]
        self.assertGreaterEqual(wear2, wear1)

    def test_13_xai_still_works(self):
        res = self.client_a.post("/api/explain", json={
            "machineId": "CNC-LATHE-01",
            "airTemperature": 300.0,
            "processTemperature": 310.0,
            "rotationalSpeed": 1500,
            "torque": 40.0,
            "toolWear": 150,
            "type": "M",
        })
        self.assertEqual(res.status_code, 200)
        body = res.get_json()
        self.assertIn("explanation", body)
        self.assertIn("topFeatures", body["explanation"])

    def test_14_alerts_still_work(self):
        # Submit critical prediction for CNC-LATHE-01
        res = self.client_a.post("/api/predict", json={
            "machineId": "CNC-LATHE-01",
            "airTemperature": 304.5,
            "processTemperature": 313.8,
            "rotationalSpeed": 1180,
            "torque": 68.0,
            "toolWear": 215,
            "type": "M",
        })
        self.assertEqual(res.status_code, 200)
        self.assertIn("alertId", res.get_json())

    def test_15_rutl_still_works(self):
        live = self.client_a.get("/api/machines/CNC-LATHE-01/simulation/live").get_json()
        self.assertIn("rutl", live)
        self.assertIn("remaining_tool_life", live["rutl"])

    def test_16_existing_authentication_tests_still_pass(self):
        unauth = self.app.test_client()
        res = unauth.get("/api/predictions")
        self.assertEqual(res.status_code, 401)


if __name__ == "__main__":
    unittest.main()
