"""SQLite storage for FactoryGuard prediction records."""

import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_DATABASE_PATH = Path(__file__).resolve().parent / "data" / "factoryguard.db"


class PredictionRepository:
    """Keep SQLite queries separate from Flask route code."""

    def __init__(self, database_path):
        self.database_path = Path(database_path)

    def _connect(self):
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self):
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS machines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    machine_id TEXT UNIQUE NOT NULL,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    product_type TEXT NOT NULL DEFAULT 'M',
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    machine_id TEXT,
                    user_id INTEGER,
                    air_temperature REAL NOT NULL,
                    process_temperature REAL NOT NULL,
                    rotational_speed REAL NOT NULL,
                    torque REAL NOT NULL,
                    tool_wear REAL NOT NULL,
                    product_type TEXT NOT NULL,
                    condition TEXT NOT NULL,
                    failure_risk REAL NOT NULL,
                    no_failure_probability REAL NOT NULL,
                    machine_failure_probability REAL NOT NULL,
                    recommendation TEXT NOT NULL,
                    risk_label TEXT NOT NULL,
                    maintenance_priority TEXT NOT NULL DEFAULT 'Routine',
                    maintenance_disclaimer TEXT NOT NULL DEFAULT ''
                )
                """
            )
            existing_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(predictions)").fetchall()
            }
            if "maintenance_priority" not in existing_columns:
                connection.execute(
                    "ALTER TABLE predictions ADD COLUMN maintenance_priority TEXT NOT NULL DEFAULT 'Routine'"
                )
            if "maintenance_disclaimer" not in existing_columns:
                connection.execute(
                    "ALTER TABLE predictions ADD COLUMN maintenance_disclaimer TEXT NOT NULL DEFAULT ''"
                )
            if "user_id" not in existing_columns:
                connection.execute(
                    "ALTER TABLE predictions ADD COLUMN user_id INTEGER"
                )
            connection.execute(
                """
                UPDATE predictions
                SET maintenance_priority = CASE condition
                    WHEN 'Normal' THEN 'Routine'
                    WHEN 'Warning' THEN 'Planned'
                    WHEN 'Critical' THEN 'Immediate'
                END,
                recommendation = CASE condition
                    WHEN 'Normal' THEN 'Continue normal monitoring and scheduled maintenance.'
                    WHEN 'Warning' THEN 'Schedule an inspection and preventive maintenance review.'
                    WHEN 'Critical' THEN 'Arrange prompt inspection before continued operation.'
                END,
                maintenance_disclaimer = 'Decision-support suggestion only; it does not guarantee machine failure.'
                WHERE maintenance_disclaimer = ''
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS maintenance_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    machine_id TEXT NOT NULL,
                    user_id INTEGER,
                    maintenance_date TEXT NOT NULL,
                    maintenance_type TEXT NOT NULL,
                    issue TEXT NOT NULL,
                    action_taken TEXT NOT NULL,
                    notes TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            m_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(maintenance_records)").fetchall()
            }
            if "user_id" not in m_columns:
                connection.execute("ALTER TABLE maintenance_records ADD COLUMN user_id INTEGER")

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    machine_id TEXT,
                    user_id INTEGER,
                    timestamp TEXT NOT NULL,
                    condition TEXT NOT NULL,
                    failure_risk REAL NOT NULL,
                    message TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'Active',
                    resolved_at TEXT
                )
                """
            )
            a_columns = {
                row["name"] for row in connection.execute("PRAGMA table_info(alerts)").fetchall()
            }
            if "user_id" not in a_columns:
                connection.execute("ALTER TABLE alerts ADD COLUMN user_id INTEGER")

    def register_machine(self, machine_id, user_id, name=None, product_type="M"):
        """Register or update a machine to a specific user idempotently."""
        created_at = datetime.now(timezone.utc).isoformat()
        machine_name = name or machine_id
        with closing(self._connect()) as connection, connection:
            existing = connection.execute(
                "SELECT * FROM machines WHERE machine_id = ?", (machine_id,)
            ).fetchone()
            if existing is not None:
                connection.execute(
                    "UPDATE machines SET user_id = ?, name = ?, product_type = ? WHERE machine_id = ?",
                    (user_id, machine_name, product_type.upper(), machine_id),
                )
            else:
                connection.execute(
                    """
                    INSERT INTO machines (machine_id, user_id, name, product_type, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (machine_id, user_id, machine_name, product_type.upper(), created_at),
                )
            row = connection.execute(
                "SELECT * FROM machines WHERE machine_id = ?", (machine_id,)
            ).fetchone()
            return dict(row)

    def get_machine(self, machine_id):
        with closing(self._connect()) as connection:
            row = connection.execute("SELECT * FROM machines WHERE machine_id = ?", (machine_id,)).fetchone()
            return dict(row) if row else None

    def user_owns_machine(self, user_id, role, machine_id):
        if role == "Admin":
            return True
        if not user_id or not machine_id:
            return False
        with closing(self._connect()) as connection:
            m_row = connection.execute(
                "SELECT user_id FROM machines WHERE machine_id = ?", (machine_id,)
            ).fetchone()
            if m_row is not None:
                return int(m_row["user_id"]) == int(user_id)
            # If not in machines table yet, check if predictions exist for this machine
            p_row = connection.execute(
                "SELECT user_id FROM predictions WHERE machine_id = ? LIMIT 1", (machine_id,)
            ).fetchone()
            if p_row is not None and p_row["user_id"] is not None:
                return int(p_row["user_id"]) == int(user_id)
            # If no machine or prediction record exists yet, allow initial creation
            return True

    def get_accessible_machine_ids(self, user_id=None, role=None):
        if role == "Admin" or user_id is None:
            return None
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT machine_id FROM machines WHERE user_id = ?", (user_id,)
            ).fetchall()
            ids = {r["machine_id"] for r in rows}
            p_rows = connection.execute(
                "SELECT DISTINCT machine_id FROM predictions WHERE user_id = ? AND machine_id IS NOT NULL", (user_id,)
            ).fetchall()
            ids.update(r["machine_id"] for r in p_rows)
            return ids

    def reset_demo_data(self, machine_ids):
        """Safely clear predictions and active alerts for demo machines before reseeding."""
        if not machine_ids:
            return
        placeholders = ",".join("?" for _ in machine_ids)
        with closing(self._connect()) as connection, connection:
            connection.execute(
                f"DELETE FROM predictions WHERE machine_id IN ({placeholders})", tuple(machine_ids)
            )
            connection.execute(
                f"DELETE FROM alerts WHERE machine_id IN ({placeholders})", tuple(machine_ids)
            )

    def create(self, payload, prediction, user_id=None):
        timestamp = datetime.now(timezone.utc).isoformat()
        machine_id = payload.get("machineId")
        with closing(self._connect()) as connection, connection:
            cursor = connection.execute(
                """
                INSERT INTO predictions (
                    timestamp, machine_id, user_id, air_temperature, process_temperature,
                    rotational_speed, torque, tool_wear, product_type, condition,
                    failure_risk, no_failure_probability, machine_failure_probability,
                    recommendation, risk_label, maintenance_priority, maintenance_disclaimer
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    timestamp, machine_id, user_id, payload["airTemperature"],
                    payload["processTemperature"], payload["rotationalSpeed"],
                    payload["torque"], payload["toolWear"], payload["type"].upper(),
                    prediction["condition"], prediction["failureRisk"],
                    prediction["probabilities"]["noFailure"],
                    prediction["probabilities"]["machineFailure"],
                    prediction["recommendation"], prediction["riskLabel"],
                    prediction["maintenancePriority"], prediction["maintenanceDisclaimer"],
                ),
            )
            return cursor.lastrowid

    def create_alert_if_needed(self, payload, prediction, user_id=None):
        """Create an in-application alert for Warning or Critical conditions without duplicate spam."""
        condition = prediction.get("condition")
        if condition not in ("Warning", "Critical"):
            return None

        machine_id = payload.get("machineId")
        with closing(self._connect()) as connection, connection:
            # Prevent spamming duplicate active alerts for the same machine and condition
            existing = connection.execute(
                "SELECT id FROM alerts WHERE machine_id = ? AND condition = ? AND status = 'Active'",
                (machine_id, condition),
            ).fetchone()
            if existing is not None:
                return existing["id"]

            timestamp = datetime.now(timezone.utc).isoformat()
            machine_name = machine_id or "Unidentified machine"
            wear = payload.get("toolWear", "N/A")
            torque = payload.get("torque", "N/A")
            speed = payload.get("rotationalSpeed", "N/A")
            rec = prediction.get("recommendation", "Inspect machine.")

            if condition == "Critical":
                message = (
                    f"{machine_name} detected in CRITICAL condition with a "
                    f"{prediction['failureRisk']}% model failure risk score. "
                    f"[Telemetry: Wear {wear} min, Torque {torque} Nm, Speed {speed} RPM]. "
                    f"Recommended Action: {rec}"
                )
            else:
                message = (
                    f"{machine_name} detected in WARNING condition with a "
                    f"{prediction['failureRisk']}% model failure risk score. "
                    f"[Telemetry: Wear {wear} min, Torque {torque} Nm, Speed {speed} RPM]. "
                    f"Recommended Action: {rec}"
                )

            cursor = connection.execute(
                """
                INSERT INTO alerts (machine_id, user_id, timestamp, condition, failure_risk, message, status)
                VALUES (?, ?, ?, ?, ?, ?, 'Active')
                """,
                (machine_id, user_id, timestamp, condition, prediction["failureRisk"], message),
            )
            return cursor.lastrowid

    @staticmethod
    def _to_alert(row):
        return {
            "id": row["id"], "machineId": row["machine_id"], "timestamp": row["timestamp"],
            "condition": row["condition"], "failureRisk": row["failure_risk"],
            "message": row["message"], "status": row["status"], "resolvedAt": row["resolved_at"],
        }

    def list_alerts(self, user_id=None, role=None):
        accessible_ids = self.get_accessible_machine_ids(user_id, role)
        with closing(self._connect()) as connection, connection:
            if accessible_ids is None:
                rows = connection.execute(
                    "SELECT * FROM alerts ORDER BY CASE status WHEN 'Active' THEN 0 ELSE 1 END, id DESC"
                ).fetchall()
            elif not accessible_ids:
                rows = []
            else:
                placeholders = ",".join("?" for _ in accessible_ids)
                rows = connection.execute(
                    f"SELECT * FROM alerts WHERE machine_id IN ({placeholders}) ORDER BY CASE status WHEN 'Active' THEN 0 ELSE 1 END, id DESC",
                    tuple(accessible_ids),
                ).fetchall()
        return [self._to_alert(row) for row in rows]

    def resolve_alert(self, alert_id, user_id=None, role=None):
        resolved_at = datetime.now(timezone.utc).isoformat()
        with closing(self._connect()) as connection, connection:
            row = connection.execute("SELECT * FROM alerts WHERE id = ?", (alert_id,)).fetchone()
            if row is None:
                return None
            if not self.user_owns_machine(user_id, role, row["machine_id"]):
                return None
            connection.execute(
                "UPDATE alerts SET status = 'Resolved', resolved_at = ? WHERE id = ? AND status = 'Active'",
                (resolved_at, alert_id),
            )
            updated = connection.execute("SELECT * FROM alerts WHERE id = ?", (alert_id,)).fetchone()
        return self._to_alert(updated) if updated else None

    @staticmethod
    def _to_api_record(row):
        return {
            "id": row["id"],
            "timestamp": row["timestamp"],
            "machineId": row["machine_id"],
            "inputs": {
                "airTemperature": row["air_temperature"],
                "processTemperature": row["process_temperature"],
                "rotationalSpeed": row["rotational_speed"],
                "torque": row["torque"],
                "toolWear": row["tool_wear"],
                "type": row["product_type"],
            },
            "condition": row["condition"],
            "failureRisk": row["failure_risk"],
            "probabilities": {
                "noFailure": row["no_failure_probability"],
                "machineFailure": row["machine_failure_probability"],
            },
            "recommendation": row["recommendation"],
            "riskLabel": row["risk_label"],
            "maintenancePriority": row["maintenance_priority"],
            "maintenanceDisclaimer": row["maintenance_disclaimer"],
        }

    def list_all(self, user_id=None, role=None):
        accessible_ids = self.get_accessible_machine_ids(user_id, role)
        with closing(self._connect()) as connection, connection:
            if accessible_ids is None:
                rows = connection.execute("SELECT * FROM predictions ORDER BY id DESC").fetchall()
            elif not accessible_ids:
                rows = []
            else:
                placeholders = ",".join("?" for _ in accessible_ids)
                rows = connection.execute(
                    f"SELECT * FROM predictions WHERE machine_id IN ({placeholders}) ORDER BY id DESC",
                    tuple(accessible_ids),
                ).fetchall()
        return [self._to_api_record(row) for row in rows]

    def get_by_id(self, prediction_id, user_id=None, role=None):
        with closing(self._connect()) as connection, connection:
            row = connection.execute("SELECT * FROM predictions WHERE id = ?", (prediction_id,)).fetchone()
        if not row:
            return None
        if not self.user_owns_machine(user_id, role, row["machine_id"]):
            return None
        return self._to_api_record(row)

    def dashboard_summary(self, user_id=None, role=None):
        """Return dashboard aggregates calculated from the saved records scoped to user."""
        accessible_ids = self.get_accessible_machine_ids(user_id, role)
        with closing(self._connect()) as connection, connection:
            if accessible_ids is None:
                totals = connection.execute(
                    """
                    SELECT COUNT(*) AS total_predictions,
                           COALESCE(AVG(failure_risk), 0) AS average_risk,
                           COALESCE(SUM(condition = 'Normal'), 0) AS normal_count,
                           COALESCE(SUM(condition = 'Warning'), 0) AS warning_count,
                           COALESCE(SUM(condition = 'Critical'), 0) AS critical_count
                    FROM predictions
                    """
                ).fetchone()
                recent_rows = connection.execute(
                    "SELECT * FROM predictions ORDER BY id DESC LIMIT 8"
                ).fetchall()
                active_alert_count = connection.execute(
                    "SELECT COUNT(*) AS count FROM alerts WHERE status = 'Active'"
                ).fetchone()["count"]
                machine_rows = connection.execute(
                    """
                    SELECT p.* FROM predictions p
                    INNER JOIN (
                        SELECT machine_id, MAX(id) AS latest_id
                        FROM predictions
                        WHERE machine_id IS NOT NULL AND machine_id != ''
                        GROUP BY machine_id
                    ) latest ON p.id = latest.latest_id
                    ORDER BY p.failure_risk DESC, p.machine_id ASC
                    """
                ).fetchall()
            elif not accessible_ids:
                return {
                    "totalPredictions": 0,
                    "conditionCounts": {"Normal": 0, "Warning": 0, "Critical": 0},
                    "averageFailureRisk": 0.0,
                    "activeAlertCount": 0,
                    "recentPredictions": [],
                    "machineStatuses": [],
                }
            else:
                placeholders = ",".join("?" for _ in accessible_ids)
                totals = connection.execute(
                    f"""
                    SELECT COUNT(*) AS total_predictions,
                           COALESCE(AVG(failure_risk), 0) AS average_risk,
                           COALESCE(SUM(condition = 'Normal'), 0) AS normal_count,
                           COALESCE(SUM(condition = 'Warning'), 0) AS warning_count,
                           COALESCE(SUM(condition = 'Critical'), 0) AS critical_count
                    FROM predictions
                    WHERE machine_id IN ({placeholders})
                    """,
                    tuple(accessible_ids),
                ).fetchone()
                recent_rows = connection.execute(
                    f"SELECT * FROM predictions WHERE machine_id IN ({placeholders}) ORDER BY id DESC LIMIT 8",
                    tuple(accessible_ids),
                ).fetchall()
                active_alert_count = connection.execute(
                    f"SELECT COUNT(*) AS count FROM alerts WHERE status = 'Active' AND machine_id IN ({placeholders})",
                    tuple(accessible_ids),
                ).fetchone()["count"]
                machine_rows = connection.execute(
                    f"""
                    SELECT p.* FROM predictions p
                    INNER JOIN (
                        SELECT machine_id, MAX(id) AS latest_id
                        FROM predictions
                        WHERE machine_id IN ({placeholders})
                        GROUP BY machine_id
                    ) latest ON p.id = latest.latest_id
                    ORDER BY p.failure_risk DESC, p.machine_id ASC
                    """,
                    tuple(accessible_ids),
                ).fetchall()

        return {
            "totalPredictions": totals["total_predictions"],
            "conditionCounts": {
                "Normal": totals["normal_count"],
                "Warning": totals["warning_count"],
                "Critical": totals["critical_count"],
            },
            "averageFailureRisk": round(float(totals["average_risk"]), 2),
            "activeAlertCount": active_alert_count,
            "recentPredictions": [self._to_api_record(row) for row in recent_rows],
            "machineStatuses": [self._to_api_record(row) for row in machine_rows],
        }

    def dashboard_trends(self, user_id=None, role=None):
        """Return chronological risk values for the risk-trend chart scoped to user."""
        accessible_ids = self.get_accessible_machine_ids(user_id, role)
        with closing(self._connect()) as connection, connection:
            if accessible_ids is None:
                rows = connection.execute(
                    "SELECT id, timestamp, machine_id, failure_risk, condition FROM predictions ORDER BY id ASC"
                ).fetchall()
            elif not accessible_ids:
                rows = []
            else:
                placeholders = ",".join("?" for _ in accessible_ids)
                rows = connection.execute(
                    f"SELECT id, timestamp, machine_id, failure_risk, condition FROM predictions WHERE machine_id IN ({placeholders}) ORDER BY id ASC",
                    tuple(accessible_ids),
                ).fetchall()
        return [
            {
                "id": row["id"],
                "timestamp": row["timestamp"],
                "machineId": row["machine_id"],
                "failureRisk": row["failure_risk"],
                "condition": row["condition"],
            }
            for row in rows
        ]

    def create_maintenance_record(self, record, user_id=None):
        created_at = datetime.now(timezone.utc).isoformat()
        with closing(self._connect()) as connection, connection:
            cursor = connection.execute(
                """
                INSERT INTO maintenance_records (
                    machine_id, user_id, maintenance_date, maintenance_type, issue,
                    action_taken, notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record["machineId"], user_id, record["maintenanceDate"], record["maintenanceType"],
                    record["issue"], record["actionTaken"], record["notes"], created_at,
                ),
            )
            return cursor.lastrowid

    @staticmethod
    def _to_maintenance_record(row):
        return {
            "id": row["id"], "machineId": row["machine_id"],
            "maintenanceDate": row["maintenance_date"], "maintenanceType": row["maintenance_type"],
            "issue": row["issue"], "actionTaken": row["action_taken"],
            "notes": row["notes"], "createdAt": row["created_at"],
        }

    def list_maintenance_records(self, user_id=None, role=None, machine_id=None):
        accessible_ids = self.get_accessible_machine_ids(user_id, role)
        with closing(self._connect()) as connection, connection:
            query = "SELECT * FROM maintenance_records"
            conditions = []
            parameters = []
            if machine_id:
                conditions.append("machine_id = ?")
                parameters.append(machine_id)
            if accessible_ids is not None:
                if not accessible_ids:
                    return []
                placeholders = ",".join("?" for _ in accessible_ids)
                conditions.append(f"machine_id IN ({placeholders})")
                parameters.extend(accessible_ids)
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY maintenance_date DESC, id DESC"
            rows = connection.execute(query, tuple(parameters)).fetchall()
        return [self._to_maintenance_record(row) for row in rows]

    def machine_detail(self, machine_id, user_id=None, role=None):
        if not self.user_owns_machine(user_id, role, machine_id):
            return None
        with closing(self._connect()) as connection, connection:
            latest = connection.execute(
                "SELECT * FROM predictions WHERE machine_id = ? ORDER BY id DESC LIMIT 1", (machine_id,)
            ).fetchone()
            predictions = connection.execute(
                "SELECT * FROM predictions WHERE machine_id = ? ORDER BY id DESC", (machine_id,)
            ).fetchall()
        if latest is None:
            return None
        return {
            "machineId": machine_id,
            "latestPrediction": self._to_api_record(latest),
            "predictions": [self._to_api_record(row) for row in predictions],
            "maintenanceRecords": self.list_maintenance_records(user_id=user_id, role=role, machine_id=machine_id),
        }


class UserRepository:
    """Keep user storage separate from prediction and maintenance records."""

    def __init__(self, database_path):
        self.database_path = Path(database_path)

    def _connect(self):
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self):
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('Admin', 'Maintenance')),
                    created_at TEXT NOT NULL
                )
                """
            )

    def count(self):
        with closing(self._connect()) as connection:
            return connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    def create(self, username, password_hash, role):
        created_at = datetime.now(timezone.utc).isoformat()
        with closing(self._connect()) as connection, connection:
            cursor = connection.execute(
                "INSERT INTO users (username, password_hash, role, created_at) VALUES (?, ?, ?, ?)",
                (username, password_hash, role, created_at),
            )
            return cursor.lastrowid

    def get_by_username(self, username):
        with closing(self._connect()) as connection:
            return connection.execute(
                "SELECT id, username, password_hash, role, created_at FROM users WHERE username = ?",
                (username,),
            ).fetchone()
