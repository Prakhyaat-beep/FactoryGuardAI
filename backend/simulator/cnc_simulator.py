"""Send stateful, software-simulated CNC lathe telemetry to FactoryGuard."""

import argparse
from datetime import datetime
import http.cookiejar
import json
import os
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.request import HTTPCookieProcessor, Request, build_opener

import pandas as pd

from simulator.scenarios import CncLatheSimulator, SCENARIOS, TelemetryProfile


DEFAULT_DATASET = Path(__file__).resolve().parents[1] / "data" / "predictive_maintenance.csv"


def post_json(opener, url, payload):
    request = Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
    with opener.open(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def run_simulation(args):
    dataset = pd.read_csv(args.dataset)
    profile = TelemetryProfile.from_dataframe(dataset)
    simulator = CncLatheSimulator(profile, scenario=args.scenario, machine_type=args.type, seed=args.seed)
    cookie_jar = http.cookiejar.CookieJar()
    opener = build_opener(HTTPCookieProcessor(cookie_jar))
    base_url = args.base_url.rstrip("/")
    post_json(opener, f"{base_url}/api/auth/login", {"username": args.username, "password": args.password})
    print(f"Software simulation started: {args.machine} | {SCENARIOS[args.scenario]} | every {args.interval:g}s")

    sent = 0
    while args.readings == 0 or sent < args.readings:
        reading = {"machineId": args.machine, **simulator.next_reading()}
        try:
            result = post_json(opener, f"{base_url}/api/predict", reading)
        except (HTTPError, URLError, TimeoutError) as error:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Backend request failed: {error}")
        else:
            print(
                f"[{datetime.now().strftime('%H:%M:%S')}] {args.machine} | "
                f"Air {reading['airTemperature']} K | Process {reading['processTemperature']} K | "
                f"RPM {reading['rotationalSpeed']} | Torque {reading['torque']} Nm | Wear {reading['toolWear']} min\n"
                f"  -> Sent to Flask | Prediction: {result['condition'].upper()} | "
                f"Risk: {result['failureRisk']}%"
            )
        sent += 1
        if args.readings == 0 or sent < args.readings:
            time.sleep(args.interval)


def parse_args():
    parser = argparse.ArgumentParser(description="Run a software-simulated CNC lathe telemetry stream.")
    parser.add_argument("--machine", default="CNC-LATHE-01", help="Machine identifier saved with readings.")
    parser.add_argument("--interval", type=float, default=5, help="Seconds between readings; minimum 0.1.")
    parser.add_argument("--scenario", choices=sorted(SCENARIOS), default="normal")
    parser.add_argument("--type", choices=["L", "M", "H"], default="M")
    parser.add_argument("--readings", type=int, default=0, help="Number of readings; 0 runs until interrupted.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--base-url", default=os.getenv("FACTORYGUARD_API_URL", "http://localhost:5000"))
    parser.add_argument("--username", default=os.getenv("FACTORYGUARD_SIMULATOR_USERNAME"))
    parser.add_argument("--password", default=os.getenv("FACTORYGUARD_SIMULATOR_PASSWORD"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if args.interval < 0.1:
        parser.error("--interval must be at least 0.1 seconds.")
    if args.readings < 0:
        parser.error("--readings cannot be negative.")
    if not args.machine.strip() or len(args.machine) > 100:
        parser.error("--machine must be 1-100 characters.")
    if not args.dataset.is_file():
        parser.error(f"Dataset not found: {args.dataset}")
    if not args.username or not args.password:
        parser.error("Provide --username and --password, or set FACTORYGUARD_SIMULATOR_USERNAME and FACTORYGUARD_SIMULATOR_PASSWORD.")
    return args


if __name__ == "__main__":
    try:
        run_simulation(parse_args())
    except KeyboardInterrupt:
        print("\nSimulator stopped.")
