# FactoryGuard AI - Project Setup

## Architecture

```text
React + Vite frontend
        |
Flask REST API with session authentication
        |
Prediction service -> saved scikit-learn pipeline
        |
SQLite: users, predictions, maintenance records, alerts
```

The model uses the UCI AI4I 2020 Predictive Maintenance Dataset. Its inputs are air temperature, process temperature, rotational speed, torque, tool wear, and product type. `failureRisk` is a model-derived score, not a calibrated industrial failure probability.

## Prerequisites

- Python 3.10+
- Node.js 18+

## Backend setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

The API runs at `http://localhost:5000`. Set a persistent session secret before deployment:

```powershell
$env:FACTORYGUARD_SECRET_KEY = "use-a-long-random-secret-here"
```

For local development, Flask generates a temporary session secret if this variable is absent. Optional settings are `FACTORYGUARD_DATABASE_PATH`, `FACTORYGUARD_CORS_ORIGINS`, and `FACTORYGUARD_SECURE_COOKIES`.

## Frontend setup

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL (normally `http://localhost:5173`). Register an account, then log in. The first account is Admin; subsequent self-registered accounts are Maintenance users.

## ML training

From `backend/`:

```powershell
python -m ml.train
```

This trains Logistic Regression, Decision Tree, and Random Forest with the same stratified split (`random_state=42`), selects the best failure-class F1 score, and writes `backend/model/failure_model.joblib` and `backend/model/evaluation_results.json`.

The supplied `backend/data/predictive_maintenance.csv` is used when present. It uses the public AI4I schema with `Target`; the loader normalizes that target name while retaining only the six telemetry features for model input.

## CNC telemetry simulator

FactoryGuard includes a software-simulated CNC lathe stream. It sends dataset-bounded, stateful readings through the existing authenticated `POST /api/predict` endpoint. No physical CNC machine connection is claimed.

```powershell
cd backend
python -m simulator.cnc_simulator --machine CNC-LATHE-01 --interval 5 --scenario normal --username your_username --password your_password
```

Available scenarios are `normal`, `degradation`, `high_torque`, `overheating`, and `failure`. Add `--readings 5` for a finite run. The dashboard Live CNC Lathe Telemetry section polls saved readings every five seconds.

## Database

SQLite is initialized automatically at `backend/data/factoryguard.db`. The tables are `users`, `predictions`, `maintenance_records`, and `alerts`. To use a different location, set `FACTORYGUARD_DATABASE_PATH` before starting Flask.

## API endpoints

Public:

- `GET /api/health`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`
- `GET /api/models/performance`

Authenticated:

- `POST /api/predict`
- `GET /api/predictions`
- `GET /api/predictions/<id>`
- `GET /api/dashboard/summary`
- `GET /api/dashboard/trends`
- `POST /api/maintenance`
- `GET /api/maintenance?machineId=<id>`
- `GET /api/machines/<machineId>`
- `GET /api/machines/<machineId>/report`
- `GET /api/alerts`
- `PATCH /api/alerts/<id>`

## Testing and production build

```powershell
cd backend
python -m unittest discover -s tests -v

cd ..\frontend
npm run build
```

The backend tests use an isolated SQLite database and cover authentication, validation, predictions, persistence, alerts, maintenance records, dashboard data, and PDF reports. The frontend build validates the production bundle.
