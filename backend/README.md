# FactoryGuard API

This Flask application is the backend for FactoryGuard AI.

## Setup and run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

The development server listens on port 5000.

## Health endpoint

`GET /api/health` returns a small JSON response confirming that the API is available.

## Prediction endpoint

`POST /api/predict` accepts the measurements used by the AI4I trained model:

```json
{
  "airTemperature": 300.0,
  "processTemperature": 310.0,
  "rotationalSpeed": 1500,
  "torque": 40.0,
  "toolWear": 120,
  "type": "M"
}
```

Temperatures are Kelvin, rotational speed is RPM, torque is Nm, and tool wear is minutes. `type` must be `L`, `M`, or `H`.

The response includes a binary model score for `machineFailure` and `noFailure`. `failureRisk` is a model-derived score, **not** a calibrated industrial probability. `condition` is an operational triage label mapped from that score: below 20% is Normal, 20%–below 50% is Warning, and 50% or above is Critical. The two boundaries can be configured with `RISK_NORMAL_MAX_PERCENT` and `RISK_WARNING_MAX_PERCENT` environment variables.

## Prediction history

SQLite storage is initialized automatically at `backend/data/factoryguard.db`. A successful `POST /api/predict` saves its inputs and result, and adds `predictionId` to the existing prediction response. You may include an optional `machineId` text field to identify a saved record; it is not used by the ML model.

- `GET /api/predictions` returns saved records, newest first.
- `GET /api/predictions/<id>` returns one full saved record, or `404` if it does not exist.

## Dashboard data

- `GET /api/dashboard/summary` returns record totals, condition counts, average risk, recent predictions, and each identified machine's latest status.
- `GET /api/dashboard/trends` returns the saved model-risk values in chronological order.

## Maintenance decision support

Prediction responses include an explainable maintenance priority: `Normal` maps to `Routine`, `Warning` maps to `Planned`, and `Critical` maps to `Immediate`. These recommendations are deterministic decision-support suggestions, not guarantees of failure. The failure-risk value remains a model-derived indicator, not a calibrated industrial probability.

- `POST /api/maintenance` creates a maintenance record with `machineId`, `maintenanceDate`, `maintenanceType`, `issue`, `actionTaken`, and `notes`.
- `GET /api/maintenance` lists all maintenance records. Add `?machineId=<id>` to filter by machine.
- `GET /api/machines/<machineId>` returns current status, latest prediction, prediction history, and maintenance history for one machine.

## In-application alerts

Critical predictions create an active in-application alert. Normal and Warning predictions do not create alerts. No email or SMS is sent.

- `GET /api/alerts` returns active and resolved alerts.
- `PATCH /api/alerts/<id>` with `{ "status": "Resolved" }` resolves an active alert and stores its `resolvedAt` timestamp.

Set `FACTORYGUARD_DATABASE_PATH` to use another SQLite database path. This keeps database configuration separate from the repository code and makes a future migration easier.

## Authentication

Saved prediction data, maintenance records, alerts, dashboards, reports, and new predictions require a signed-in user. `GET /api/health` and the authentication endpoints remain public.

- `POST /api/auth/register` accepts `username` and `password`. The first account is an `Admin`; later self-registered accounts are `Maintenance` users.
- `POST /api/auth/login` starts an HTTP-only Flask session.
- `POST /api/auth/logout` ends the session.
- `GET /api/auth/me` returns the signed-in user.

Passwords are stored only as Werkzeug password hashes. Set `FACTORYGUARD_SECRET_KEY` to a long, random value before deployment so sessions remain valid across backend restarts. For local development, a temporary in-memory key is generated automatically.

## Test

From `backend/`, after training the model:

```powershell
python -m unittest discover -s tests -v
```
