"""Seed initial demo machine fleet with model-derived predictions."""

DEFAULT_FLEET_CONFIGS = [
    # Arjun Mehta (CNC-LATHE-01 .. 05): 2 Normal, 2 Warning, 1 Critical
    {
        "machineId": "CNC-LATHE-01",
        "name": "CNC Turning Center 01",
        "scenario": "normal",
        "telemetry": {
            "airTemperature": 298.1,
            "processTemperature": 308.6,
            "rotationalSpeed": 1550,
            "torque": 40.0,
            "toolWear": 15,
            "type": "M",
        },
    },
    {
        "machineId": "CNC-LATHE-02",
        "name": "Precision Finish Lathe 02",
        "scenario": "normal",
        "telemetry": {
            "airTemperature": 297.5,
            "processTemperature": 308.0,
            "rotationalSpeed": 1500,
            "torque": 38.0,
            "toolWear": 30,
            "type": "L",
        },
    },
    {
        "machineId": "CNC-LATHE-03",
        "name": "Heavy Roughing Lathe 03",
        "scenario": "degradation",
        "telemetry": {
            "airTemperature": 301.0,
            "processTemperature": 311.0,
            "rotationalSpeed": 1320,
            "torque": 58.0,
            "toolWear": 200,
            "type": "H",
        },
    },
    {
        "machineId": "CNC-LATHE-04",
        "name": "High-Speed Finish Lathe 04",
        "scenario": "high_torque",
        "telemetry": {
            "airTemperature": 301.0,
            "processTemperature": 311.0,
            "rotationalSpeed": 1300,
            "torque": 65.0,
            "toolWear": 180,
            "type": "L",
        },
    },
    {
        "machineId": "CNC-LATHE-05",
        "name": "Medium Turning Lathe 05",
        "scenario": "failure",
        "telemetry": {
            "airTemperature": 304.5,
            "processTemperature": 313.8,
            "rotationalSpeed": 1180,
            "torque": 68.0,
            "toolWear": 215,
            "type": "M",
        },
    },

    # Neha Sharma (CNC-LATHE-06 .. 10): 2 Normal, 1 Warning, 2 Critical
    {
        "machineId": "CNC-LATHE-06",
        "name": "Precision Turning Lathe 06",
        "scenario": "normal",
        "telemetry": {
            "airTemperature": 299.0,
            "processTemperature": 309.2,
            "rotationalSpeed": 1600,
            "torque": 42.0,
            "toolWear": 45,
            "type": "H",
        },
    },
    {
        "machineId": "CNC-LATHE-07",
        "name": "Stress-Test CNC Lathe 07",
        "scenario": "normal",
        "telemetry": {
            "airTemperature": 298.0,
            "processTemperature": 308.5,
            "rotationalSpeed": 1540,
            "torque": 39.5,
            "toolWear": 20,
            "type": "M",
        },
    },
    {
        "machineId": "CNC-LATHE-08",
        "name": "High-Wear CNC Lathe 08",
        "scenario": "overheating",
        "telemetry": {
            "airTemperature": 302.0,
            "processTemperature": 312.0,
            "rotationalSpeed": 1300,
            "torque": 56.0,
            "toolWear": 200,
            "type": "L",
        },
    },
    {
        "machineId": "CNC-LATHE-09",
        "name": "Production Turning Unit 09",
        "scenario": "failure",
        "telemetry": {
            "airTemperature": 304.0,
            "processTemperature": 313.5,
            "rotationalSpeed": 1150,
            "torque": 70.0,
            "toolWear": 220,
            "type": "H",
        },
    },
    {
        "machineId": "CNC-LATHE-10",
        "name": "Heavy Production Lathe 10",
        "scenario": "failure",
        "telemetry": {
            "airTemperature": 303.8,
            "processTemperature": 313.2,
            "rotationalSpeed": 1200,
            "torque": 67.0,
            "toolWear": 210,
            "type": "M",
        },
    },

    # Rohan Iyer (CNC-LATHE-11 .. 15): 1 Normal, 2 Warning, 2 Critical
    {
        "machineId": "CNC-LATHE-11",
        "name": "Primary Turning Unit 11",
        "scenario": "normal",
        "telemetry": {
            "airTemperature": 298.2,
            "processTemperature": 308.7,
            "rotationalSpeed": 1560,
            "torque": 40.5,
            "toolWear": 25,
            "type": "L",
        },
    },
    {
        "machineId": "CNC-LATHE-12",
        "name": "Secondary Finish Lathe 12",
        "scenario": "degradation",
        "telemetry": {
            "airTemperature": 300.2,
            "processTemperature": 310.2,
            "rotationalSpeed": 1390,
            "torque": 53.5,
            "toolWear": 205,
            "type": "M",
        },
    },
    {
        "machineId": "CNC-LATHE-13",
        "name": "High-Load Lathe 13",
        "scenario": "high_torque",
        "telemetry": {
            "airTemperature": 301.2,
            "processTemperature": 311.2,
            "rotationalSpeed": 1320,
            "torque": 62.0,
            "toolWear": 175,
            "type": "H",
        },
    },
    {
        "machineId": "CNC-LATHE-14",
        "name": "Critical Production Lathe 14",
        "scenario": "failure",
        "telemetry": {
            "airTemperature": 304.1,
            "processTemperature": 313.4,
            "rotationalSpeed": 1170,
            "torque": 68.5,
            "toolWear": 216,
            "type": "L",
        },
    },
    {
        "machineId": "CNC-LATHE-15",
        "name": "Automated Turning Lathe 15",
        "scenario": "failure",
        "telemetry": {
            "airTemperature": 304.2,
            "processTemperature": 313.5,
            "rotationalSpeed": 1160,
            "torque": 68.0,
            "toolWear": 218,
            "type": "H",
        },
    },
]

DEMO_MACHINE_ASSIGNMENTS = {
    # Arjun Mehta (01 - 05)
    "CNC-LATHE-01": "arjun.mehta",
    "CNC-LATHE-02": "arjun.mehta",
    "CNC-LATHE-03": "arjun.mehta",
    "CNC-LATHE-04": "arjun.mehta",
    "CNC-LATHE-05": "arjun.mehta",

    # Neha Sharma (06 - 10)
    "CNC-LATHE-06": "neha.sharma",
    "CNC-LATHE-07": "neha.sharma",
    "CNC-LATHE-08": "neha.sharma",
    "CNC-LATHE-09": "neha.sharma",
    "CNC-LATHE-10": "neha.sharma",

    # Rohan Iyer (11 - 15)
    "CNC-LATHE-11": "rohan.iyer",
    "CNC-LATHE-12": "rohan.iyer",
    "CNC-LATHE-13": "rohan.iyer",
    "CNC-LATHE-14": "rohan.iyer",
    "CNC-LATHE-15": "rohan.iyer",
}


def ensure_demo_users(user_repository):
    """Ensure baseline demo users exist in SQLite with hashed passwords."""
    from werkzeug.security import generate_password_hash

    demo_users = [
        ("arjun.mehta", "Arjun@123", "Maintenance"),
        ("neha.sharma", "Neha@123", "Maintenance"),
        ("rohan.iyer", "Rohan@123", "Maintenance"),
        ("admin", "admin123", "Admin"),
    ]
    user_map = {}
    for username, password, role in demo_users:
        existing = user_repository.get_by_username(username)
        if existing is None:
            user_id = user_repository.create(username, generate_password_hash(password), role)
            user_map[username] = user_id
        else:
            user_map[username] = existing["id"]
    return user_map


def seed_demo_fleet(repository, prediction_service, force_reset=False, user_repository=None):
    """Seed or refresh the 15 demo machines with model-derived predictions and user assignments."""
    user_map = {}
    if user_repository is not None:
        user_map = ensure_demo_users(user_repository)
    
    demo_ids = [cfg["machineId"] for cfg in DEFAULT_FLEET_CONFIGS]
    if force_reset:
        repository.reset_demo_data(demo_ids)

    existing_summary = repository.dashboard_summary()
    existing_machine_ids = {
        m["machineId"] for m in existing_summary.get("machineStatuses", []) if m.get("machineId")
    }

    seeded_count = 0
    distribution = {"Normal": 0, "Warning": 0, "Critical": 0}

    for cfg in DEFAULT_FLEET_CONFIGS:
        m_id = cfg["machineId"]
        target_username = DEMO_MACHINE_ASSIGNMENTS.get(m_id, "arjun.mehta")
        owner_id = user_map.get(target_username, 1)

        repository.register_machine(
            machine_id=m_id,
            user_id=owner_id,
            name=cfg.get("name", m_id),
            product_type=cfg.get("telemetry", {}).get("type", "M"),
        )

        if force_reset or m_id not in existing_machine_ids:
            payload = {"machineId": m_id, **cfg["telemetry"]}
            prediction = prediction_service.predict(payload)
            repository.create(payload, prediction, user_id=owner_id)
            repository.create_alert_if_needed(payload, prediction, user_id=owner_id)
            seeded_count += 1
            cond = prediction.get("condition", "Normal")
            if cond in distribution:
                distribution[cond] += 1

    return {
        "seededCount": seeded_count,
        "totalFleet": len(DEFAULT_FLEET_CONFIGS),
        "distribution": distribution,
        "assignments": DEMO_MACHINE_ASSIGNMENTS,
    }
