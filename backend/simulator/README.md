# CNC Lathe Telemetry Simulator

This is a software simulator, not a physical CNC connection. It reads the supplied `predictive_maintenance.csv`, derives medians, 5th/95th percentiles, and hard limits from its telemetry columns, then creates gradual stateful readings inside those empirical limits.

The supplied data has 10,000 complete rows. Telemetry ranges are air temperature 295.3-304.5 K, process temperature 305.7-313.8 K, rotational speed 1168-2886 rpm, torque 3.8-76.6 Nm, and tool wear 0-253 min. `Target` and `Failure Type` are never sent as telemetry.

Scenarios are controlled trajectories, not labels: normal returns toward medians; degradation raises tool wear and moves torque/RPM toward empirical high-load/low-speed percentiles; high torque raises torque with RPM movement; overheating raises temperatures; failure combines the abnormal trajectories. The backend model alone produces the condition and risk indicator.

Run from `backend/` after starting Flask and registering a user:

```powershell
python -m simulator.cnc_simulator --machine CNC-LATHE-01 --interval 5 --scenario normal --username your_username --password your_password
```

Use `degradation`, `high_torque`, `overheating`, or `failure` for the other scenarios. Add `--readings 5` for a finite demonstration.
