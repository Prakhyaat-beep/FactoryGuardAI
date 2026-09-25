import os
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from io import BytesIO

from flask import Flask, jsonify, request, send_file, session
from flask_cors import CORS
from database import DEFAULT_DATABASE_PATH, PredictionRepository, UserRepository
from services.auth_service import (
    AuthenticationValidationError, authenticate_user, create_user, login_required,
    validate_login, validate_registration,
)
from services.explanation_service import ExplanationService
from services.prediction_service import ModelUnavailableError, PredictionService, ValidationError
from services.maintenance_service import MaintenanceValidationError, validate_maintenance_record
from services.report_service import build_machine_report
from services.simulation_service import SimulationService
from services.seed_service import DEFAULT_FLEET_CONFIGS, seed_demo_fleet


def create_app(test_config=None):
    """Create and configure the FactoryGuard API application."""
    app = Flask(__name__)
    allowed_origins = [origin.strip() for origin in os.getenv("FACTORYGUARD_CORS_ORIGINS", "http://localhost:5173").split(",")]
    CORS(app, origins=allowed_origins, supports_credentials=True)
    app.config.from_mapping(
        DATABASE_PATH=os.getenv("FACTORYGUARD_DATABASE_PATH", str(DEFAULT_DATABASE_PATH)),
        RISK_NORMAL_MAX_PERCENT=float(os.getenv("RISK_NORMAL_MAX_PERCENT", "20")),
        RISK_WARNING_MAX_PERCENT=float(os.getenv("RISK_WARNING_MAX_PERCENT", "50")),
        SECRET_KEY=os.getenv("FACTORYGUARD_SECRET_KEY") or secrets.token_urlsafe(32),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.getenv("FACTORYGUARD_SECURE_COOKIES", "false").lower() == "true",
    )
    if test_config:
        app.config.update(test_config)
    repository = PredictionRepository(app.config["DATABASE_PATH"])
    repository.initialize()
    users = UserRepository(app.config["DATABASE_PATH"])
    users.initialize()
    prediction_service = PredictionService(
        normal_max_percent=app.config["RISK_NORMAL_MAX_PERCENT"],
        warning_max_percent=app.config["RISK_WARNING_MAX_PERCENT"],
    )
    explanation_service = ExplanationService()
    simulation_service = SimulationService(
        repository=repository,
        prediction_service=prediction_service,
        explanation_service=explanation_service,
    )

    if not app.config.get("TESTING"):
        try:
            seed_demo_fleet(repository, prediction_service, force_reset=False, user_repository=users)
        except Exception as err:
            app.logger.warning(f"Initial fleet seed skipped: {err}")

    @app.get("/api/health")
    def health_check():
        return jsonify(
            {
                "status": "ok",
                "message": "FactoryGuard API is running",
            }
        )

    @app.post("/api/auth/register")
    def register():
        if not request.is_json:
            return jsonify({"error": "Request body must be valid JSON."}), 400
        try:
            username, password = validate_registration(request.get_json(silent=True))
            if users.get_by_username(username) is not None:
                return jsonify({"error": "That username is already in use."}), 409
            return jsonify({"user": create_user(users, username, password)}), 201
        except AuthenticationValidationError as error:
            return jsonify({"error": str(error)}), 400

    @app.post("/api/auth/login")
    def login():
        if not request.is_json:
            return jsonify({"error": "Request body must be valid JSON."}), 400
        try:
            username, password = validate_login(request.get_json(silent=True))
        except AuthenticationValidationError as error:
            return jsonify({"error": str(error)}), 400
        user = authenticate_user(users, username, password)
        if user is None:
            return jsonify({"error": "Invalid username or password."}), 401
        session.clear()
        session["user"] = user
        return jsonify({"user": user})

    @app.post("/api/auth/logout")
    def logout():
        session.clear()
        return jsonify({"message": "Logged out."})

    @app.get("/api/auth/me")
    def current_user():
        user = session.get("user")
        if user is None:
            return jsonify({"error": "Authentication is required."}), 401
        return jsonify({"user": user})

    @app.post("/api/predict")
    @login_required
    def predict():
        if not request.is_json:
            return jsonify({"error": "Request body must be valid JSON."}), 400

        payload = request.get_json(silent=True)
        if payload is None:
            return jsonify({"error": "Request body must contain valid JSON."}), 400

        user = session["user"]
        machine_id = payload.get("machineId")
        if machine_id:
            machine_id = str(machine_id).strip()
            payload["machineId"] = machine_id
            if not repository.user_owns_machine(user["id"], user["role"], machine_id):
                return jsonify({"error": "Access denied to specified machine."}), 403
            repository.register_machine(machine_id, user["id"], name=machine_id, product_type=payload.get("type", "M"))

        try:
            prediction = prediction_service.predict(payload)
            prediction_id = repository.create(payload, prediction, user_id=user["id"])
            alert_id = repository.create_alert_if_needed(payload, prediction, user_id=user["id"])
            explanation = explanation_service.explain(payload, prediction)
            response = {**prediction, "predictionId": prediction_id, "explanation": explanation}
            if alert_id is not None:
                response["alertId"] = alert_id

            if machine_id:
                simulation_service.update_machine_state_from_prediction(machine_id, payload, prediction, explanation)

            return jsonify(response)
        except ValidationError as error:
            return jsonify({"error": str(error)}), 400
        except ModelUnavailableError:
            return jsonify({"error": "Prediction model is unavailable. Train the model before predicting."}), 503
        except Exception:
            app.logger.exception("Unexpected prediction error")
            return jsonify({"error": "Unable to generate a prediction."}), 500

    @app.get("/api/predictions")
    @login_required
    def list_predictions():
        user = session["user"]
        return jsonify({"predictions": repository.list_all(user_id=user["id"], role=user["role"])})

    @app.get("/api/predictions/<int:prediction_id>")
    @login_required
    def get_prediction(prediction_id):
        user = session["user"]
        prediction = repository.get_by_id(prediction_id, user_id=user["id"], role=user["role"])
        if prediction is None:
            return jsonify({"error": "Prediction record not found or access denied."}), 404
        return jsonify(prediction)

    @app.get("/api/dashboard/summary")
    @login_required
    def dashboard_summary():
        user = session["user"]
        return jsonify(repository.dashboard_summary(user_id=user["id"], role=user["role"]))

    @app.get("/api/dashboard/trends")
    @login_required
    def dashboard_trends():
        user = session["user"]
        return jsonify({"trends": repository.dashboard_trends(user_id=user["id"], role=user["role"])})

    @app.get("/api/models/performance")
    def model_performance():
        results_path = Path(__file__).resolve().parent / "model" / "evaluation_results.json"
        try:
            return jsonify(json.loads(results_path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            return jsonify({"error": "Model experiment results are unavailable. Run training first."}), 503

    @app.post("/api/maintenance")
    @login_required
    def create_maintenance_record():
        if not request.is_json:
            return jsonify({"error": "Request body must be valid JSON."}), 400
        payload = request.get_json(silent=True)
        if payload is None:
            return jsonify({"error": "Request body must contain valid JSON."}), 400
        user = session["user"]
        try:
            record = validate_maintenance_record(payload)
            if not repository.user_owns_machine(user["id"], user["role"], record["machineId"]):
                return jsonify({"error": "Access denied to this machine."}), 403
            record_id = repository.create_maintenance_record(record, user_id=user["id"])
            return jsonify({**record, "id": record_id}), 201
        except MaintenanceValidationError as error:
            return jsonify({"error": str(error)}), 400

    @app.get("/api/maintenance")
    @login_required
    def list_maintenance_records():
        user = session["user"]
        machine_id = request.args.get("machineId")
        if machine_id and not repository.user_owns_machine(user["id"], user["role"], machine_id):
            return jsonify({"error": "Access denied to specified machine."}), 403
        return jsonify({"maintenanceRecords": repository.list_maintenance_records(user_id=user["id"], role=user["role"], machine_id=machine_id)})

    @app.get("/api/machines")
    @login_required
    def list_machines():
        """Return list of fleet machines accessible to current user with latest status."""
        user = session["user"]
        summary = repository.dashboard_summary(user_id=user["id"], role=user["role"])
        existing_statuses = {m["machineId"]: m for m in summary.get("machineStatuses", []) if m.get("machineId")}
        
        fleet_list = []
        seen = set()

        accessible_ids = repository.get_accessible_machine_ids(user_id=user["id"], role=user["role"])

        for cfg in DEFAULT_FLEET_CONFIGS:
            m_id = cfg["machineId"]
            if accessible_ids is not None and m_id not in accessible_ids:
                continue
            seen.add(m_id)
            if m_id in existing_statuses:
                fleet_list.append(existing_statuses[m_id])
            else:
                payload = {"machineId": m_id, **cfg["telemetry"]}
                try:
                    pred = prediction_service.predict(payload)
                    pred["machineId"] = m_id
                    pred["inputs"] = cfg["telemetry"]
                    pred["timestamp"] = datetime.now(timezone.utc).isoformat()
                    fleet_list.append(pred)
                except Exception:
                    pass

        for m_id, record in existing_statuses.items():
            if m_id not in seen:
                if accessible_ids is not None and m_id not in accessible_ids:
                    continue
                seen.add(m_id)
                fleet_list.append(record)

        return jsonify({"machines": fleet_list})

    @app.post("/api/fleet/reseed")
    @login_required
    def reseed_fleet():
        """Reseed/refresh demo fleet to balanced Normal/Warning/Critical distribution."""
        result = seed_demo_fleet(repository, prediction_service, force_reset=True, user_repository=users)
        return jsonify({
            "message": "Demo fleet refreshed successfully.",
            **result
        })

    @app.post("/api/machines/<machine_id>/simulation/start")
    @login_required
    def start_machine_simulation(machine_id):
        """Start or resume automatic CNC lathe telemetry simulation."""
        user = session["user"]
        if not repository.user_owns_machine(user["id"], user["role"], machine_id):
            return jsonify({"error": "Access denied to this machine."}), 403
        data = request.get_json(silent=True) or {}
        scenario = data.get("scenario", "normal")
        machine_type = data.get("type", "M")
        status = simulation_service.start_or_resume(machine_id, scenario=scenario, machine_type=machine_type)
        return jsonify(status)

    @app.get("/api/machines/<machine_id>/simulation/live")
    @login_required
    def get_machine_live_telemetry(machine_id):
        """Fetch live telemetry, ML prediction, XAI explanation, and alerts for a machine."""
        user = session["user"]
        if not repository.user_owns_machine(user["id"], user["role"], machine_id):
            return jsonify({"error": "Access denied to this machine."}), 403
        status = simulation_service.get_machine_status(machine_id)
        return jsonify(status)

    @app.post("/api/machines/<machine_id>/simulation/scenario")
    @login_required
    def set_machine_simulation_scenario(machine_id):
        """Adjust operational scenario (normal, degradation, high_torque, overheating, failure)."""
        user = session["user"]
        if not repository.user_owns_machine(user["id"], user["role"], machine_id):
            return jsonify({"error": "Access denied to this machine."}), 403
        data = request.get_json(silent=True) or {}
        scenario = data.get("scenario")
        if not scenario:
            return jsonify({"error": "scenario is required."}), 400
        try:
            status = simulation_service.set_scenario(machine_id, scenario)
            return jsonify(status)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

    @app.post("/api/machines/<machine_id>/simulation/stop")
    @login_required
    def stop_machine_simulation(machine_id):
        """Pause CNC lathe telemetry simulation."""
        user = session["user"]
        if not repository.user_owns_machine(user["id"], user["role"], machine_id):
            return jsonify({"error": "Access denied to this machine."}), 403
        status = simulation_service.stop_machine(machine_id)
        return jsonify(status)

    @app.post("/api/explain")
    @login_required
    def explain_parameters():
        """Compute model-grounded feature attributions for a set of machine parameters."""
        user = session["user"]
        payload = request.get_json(silent=True) or {}
        machine_id = payload.get("machineId")
        if machine_id and not repository.user_owns_machine(user["id"], user["role"], machine_id):
            return jsonify({"error": "Access denied to specified machine."}), 403
        try:
            prediction = prediction_service.predict(payload)
            explanation = explanation_service.explain(payload, prediction)
            return jsonify({"prediction": prediction, "explanation": explanation})
        except ValidationError as error:
            return jsonify({"error": str(error)}), 400
        except ModelUnavailableError:
            return jsonify({"error": "Model unavailable."}), 503
        except Exception:
            app.logger.exception("Explain error")
            return jsonify({"error": "Unable to compute explanation."}), 500

    @app.get("/api/machines/<machine_id>")
    @login_required
    def machine_detail(machine_id):
        user = session["user"]
        if not repository.user_owns_machine(user["id"], user["role"], machine_id):
            return jsonify({"error": "Access denied to this machine."}), 403
        detail = repository.machine_detail(machine_id, user_id=user["id"], role=user["role"])
        if detail is None:
            return jsonify({"error": "Machine has no saved predictions."}), 404
        return jsonify(detail)

    @app.get("/api/alerts")
    @login_required
    def list_alerts():
        user = session["user"]
        return jsonify({"alerts": repository.list_alerts(user_id=user["id"], role=user["role"])})

    @app.patch("/api/alerts/<int:alert_id>")
    @login_required
    def resolve_alert(alert_id):
        user = session["user"]
        if not request.is_json:
            return jsonify({"error": "Request body must be valid JSON."}), 400
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict) or payload.get("status") != "Resolved":
            return jsonify({"error": "Only status 'Resolved' is supported."}), 400
        alert = repository.resolve_alert(alert_id, user_id=user["id"], role=user["role"])
        if alert is None:
            return jsonify({"error": "Alert not found or access denied."}), 404
        return jsonify(alert)

    @app.get("/api/machines/<machine_id>/report")
    @login_required
    def machine_report(machine_id):
        user = session["user"]
        if not repository.user_owns_machine(user["id"], user["role"], machine_id):
            return jsonify({"error": "Access denied to this machine report."}), 403
        detail = repository.machine_detail(machine_id, user_id=user["id"], role=user["role"])
        if detail is None:
            return jsonify({"error": "Machine has no saved predictions."}), 404
        try:
            pdf_bytes = build_machine_report(detail)
        except Exception:
            app.logger.exception("Could not generate machine report")
            return jsonify({"error": "Unable to generate the machine report."}), 500
        safe_machine_id = "".join(character if character.isalnum() or character in "-_" else "-" for character in machine_id).strip("-") or "machine"
        filename = f"factoryguard-{safe_machine_id}-report.pdf"
        return send_file(BytesIO(pdf_bytes), mimetype="application/pdf", as_attachment=True, download_name=filename)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")
