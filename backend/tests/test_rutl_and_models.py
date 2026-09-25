import unittest
from pathlib import Path
import json

from ml.data_loader import load_dataset
from ml.preprocess import prepare_features_and_target, build_preprocessor
from ml.train import build_models, train_and_save, EVALUATION_PATH
from ml.predict import load_trained_model
from services.rutl_service import RutlService, DOCUMENTED_EOL_THRESHOLD_MINUTES
from services.explanation_service import ExplanationService
from app import create_app


class RutlAndMultiModelTests(unittest.TestCase):
    def setUp(self):
        self.database_path = Path(__file__).resolve().parents[1] / "data" / "test_rutl_factoryguard.db"
        self.database_path.unlink(missing_ok=True)
        self.app = create_app({"TESTING": True, "DATABASE_PATH": str(self.database_path)})
        self.client = self.app.test_client()
        self.client.post("/api/auth/register", json={"username": "rutl-user", "password": "secure-password-123"})
        self.client.post("/api/auth/login", json={"username": "rutl-user", "password": "secure-password-123"})

    def tearDown(self):
        self.database_path.unlink(missing_ok=True)

    def test_svm_and_gradient_boosting_models_exist(self):
        """1 & 2: Verify SVM and GradientBoosting are in the model dictionary."""
        models = build_models()
        self.assertIn("svm", models)
        self.assertIn("gradient_boosting", models)
        self.assertIn("logistic_regression", models)
        self.assertIn("decision_tree", models)
        self.assertIn("random_forest", models)
        self.assertEqual(len(models), 5)

    def test_five_model_evaluation_and_selection(self):
        """3 & 4: Verify 5-model evaluation produces metrics for all 5 and selects best by F1."""
        eval_data = json.loads(EVALUATION_PATH.read_text(encoding="utf-8"))
        models = eval_data["models"]
        self.assertEqual(len(models), 5)
        for name in ["logistic_regression", "decision_tree", "random_forest", "svm", "gradient_boosting"]:
            self.assertIn(name, models)
            self.assertIn("accuracy", models[name])
            self.assertIn("precision", models[name])
            self.assertIn("recall", models[name])
            self.assertIn("f1_score", models[name])
            self.assertIn("roc_auc", models[name])
            self.assertIn("training_time_seconds", models[name])

        # Verify selected model is the one with maximum F1 score
        expected_selected = max(models, key=lambda m: models[m]["f1_score"])
        self.assertEqual(eval_data["selected_model"], expected_selected)

    def test_prediction_using_trained_pipeline(self):
        """5: Verify prediction works using the active production pipeline."""
        model = load_trained_model()
        self.assertIsNotNone(model)
        res = self.client.post("/api/predict", json={
            "airTemperature": 300.0,
            "processTemperature": 310.0,
            "rotationalSpeed": 1500.0,
            "torque": 40.0,
            "toolWear": 50.0,
            "type": "M",
            "machineId": "CNC-TEST",
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("condition", data)
        self.assertIn("failureRisk", data)
        self.assertIn("probabilities", data)

    def test_rutl_calculation_with_increasing_wear(self):
        """6 & 7: Verify Remaining Useful Tool Life decreases as tool wear accumulates."""
        rutl_service = RutlService(eol_threshold=220.0)

        # Early life
        rutl_low = rutl_service.estimate(50.0, [{"toolWear": 49.0}, {"toolWear": 50.0}])
        self.assertEqual(rutl_low["current_tool_wear"], 50.0)
        self.assertEqual(rutl_low["remaining_tool_life"], 170.0)
        self.assertEqual(rutl_low["tool_condition"], "Good")

        # Moderate life
        rutl_mid = rutl_service.estimate(160.0, [{"toolWear": 159.0}, {"toolWear": 160.0}])
        self.assertEqual(rutl_mid["current_tool_wear"], 160.0)
        self.assertEqual(rutl_mid["remaining_tool_life"], 60.0)
        self.assertEqual(rutl_mid["tool_condition"], "Moderate Wear")
        self.assertLess(rutl_mid["remaining_tool_life"], rutl_low["remaining_tool_life"])

        # Degrading critical life
        rutl_high = rutl_service.estimate(210.0, [{"toolWear": 208.5}, {"toolWear": 210.0}])
        self.assertEqual(rutl_high["remaining_tool_life"], 10.0)
        self.assertEqual(rutl_high["tool_condition"], "Degrading")
        self.assertLess(rutl_high["remaining_tool_life"], rutl_mid["remaining_tool_life"])

    def test_rutl_never_becomes_negative(self):
        """8: RUTL must never drop below 0 even if wear exceeds 220 min."""
        rutl_service = RutlService(eol_threshold=220.0)
        rutl_over = rutl_service.estimate(245.0, [{"toolWear": 240.0}, {"toolWear": 245.0}])
        self.assertEqual(rutl_over["remaining_tool_life"], 0.0)
        self.assertEqual(rutl_over["remaining_tool_life_percent"], 0.0)
        self.assertEqual(rutl_over["estimated_remaining_minutes"], 0.0)
        self.assertEqual(rutl_over["tool_condition"], "Critical - End of Life")

    def test_rutl_insufficient_history_handling(self):
        """9: RUTL handles missing or 0/1 reading history safely without crashing."""
        rutl_service = RutlService(eol_threshold=220.0)
        # Empty history
        rutl_empty = rutl_service.estimate(30.0, [])
        self.assertEqual(rutl_empty["remaining_tool_life"], 190.0)
        self.assertIn("insufficient history", rutl_empty["confidence"].lower())

        # Single reading history
        rutl_single = rutl_service.estimate(30.0, [{"toolWear": 30.0}])
        self.assertEqual(rutl_single["remaining_tool_life"], 190.0)

    def test_rutl_extreme_invalid_telemetry_handling(self):
        """10: RUTL handles invalid types or negative wear gracefully."""
        rutl_service = RutlService(eol_threshold=220.0)
        rutl_neg = rutl_service.estimate(-10.0, None)
        self.assertEqual(rutl_neg["current_tool_wear"], 0.0)
        self.assertEqual(rutl_neg["remaining_tool_life"], 220.0)

        rutl_invalid = rutl_service.estimate("invalid", None)
        self.assertEqual(rutl_invalid["current_tool_wear"], 0.0)

    def test_simulation_rutl_integration(self):
        """11: Verify simulation live endpoint returns integrated RUTL alongside telemetry and prediction."""
        res = self.client.post("/api/machines/CNC-RUTL-01/simulation/start", json={"scenario": "normal", "type": "M"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("rutl", data)
        rutl = data["rutl"]
        self.assertIn("current_tool_wear", rutl)
        self.assertIn("remaining_tool_life", rutl)
        self.assertIn("estimated_remaining_minutes", rutl)
        self.assertIn("wear_rate", rutl)
        self.assertIn("tool_condition", rutl)
        self.assertIn("method", rutl)
        self.assertEqual(rutl["method"], "degradation_based_estimation")

    def test_xai_compatibility_across_models(self):
        """12: Verify XAI provides transparent explanations without errors."""
        xai = ExplanationService()
        sample = {
            "airTemperature": 300.0,
            "processTemperature": 310.0,
            "rotationalSpeed": 1300.0,
            "torque": 65.0,
            "toolWear": 210.0,
            "type": "M",
        }
        pred = {"condition": "Critical", "failureRisk": 92.0}
        exp = xai.explain(sample, pred)
        self.assertIn("topFeatures", exp)
        self.assertIn("summary", exp)
        self.assertTrue(len(exp["topFeatures"]) > 0)

    def test_fleet_reseeding_balanced_distribution(self):
        """Verify demo fleet reseeding produces balanced Normal / Warning / Critical predictions."""
        reseed_res = self.client.post("/api/fleet/reseed")
        self.assertEqual(reseed_res.status_code, 200)
        reseed_data = reseed_res.get_json()
        self.assertEqual(reseed_data["totalFleet"], 15)
        self.assertEqual(reseed_data["distribution"]["Normal"], 5)
        self.assertEqual(reseed_data["distribution"]["Warning"], 5)
        self.assertEqual(reseed_data["distribution"]["Critical"], 5)

        # Verify /api/machines returns all 15 machines for admin
        machines_res = self.client.get("/api/machines")
        self.assertEqual(machines_res.status_code, 200)
        machines = machines_res.get_json()["machines"]
        self.assertEqual(len(machines), 15)

        conditions = [m["condition"] for m in machines]
        self.assertEqual(conditions.count("Normal"), 5)
        self.assertEqual(conditions.count("Warning"), 5)
        self.assertEqual(conditions.count("Critical"), 5)

        # Verify dashboard summary matches
        summary_res = self.client.get("/api/dashboard/summary")
        self.assertEqual(summary_res.status_code, 200)
        summary = summary_res.get_json()
        self.assertEqual(summary["conditionCounts"]["Normal"], 5)
        self.assertEqual(summary["conditionCounts"]["Warning"], 5)
        self.assertEqual(summary["conditionCounts"]["Critical"], 5)


if __name__ == "__main__":
    unittest.main()
