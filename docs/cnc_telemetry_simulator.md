# CNC Lathe Telemetry Simulator

## Purpose

FactoryGuard now includes a software-based CNC lathe telemetry simulator. It is a demonstration and monitoring component, not a connection to a physical CNC machine. The simulator generates gradual readings and calls the existing authenticated prediction API. Flask validates the values, reuses the saved ML pipeline, and saves the resulting prediction through the existing SQLite repository.

## Supplied dataset inspection

`predictive_maintenance.csv` contains 10,000 rows and no missing values.

| Field | Observed range | Observation |
| --- | --- | --- |
| Air temperature [K] | 295.3 to 304.5 | Strongly correlated with process temperature (0.876). |
| Process temperature [K] | 305.7 to 313.8 | Used with air temperature in overheating trajectory. |
| Rotational speed [rpm] | 1168 to 2886 | Strong negative correlation with torque (-0.875). |
| Torque [Nm] | 3.8 to 76.6 | Failure rows have a higher median torque (53.7 versus 39.9). |
| Tool wear [min] | 0 to 253 | Failure rows have a higher median wear (165 versus 107). |

`Type` values are L (6000), M (2997), and H (1003). `Target` contains 9661 non-failures and 339 failures. `Failure Type` is not used as telemetry. The loader normalizes `Target` to the existing internal `Machine failure` target only during training; neither output field is passed to the model as an input.

## Scenario behavior

All scenario signals are clamped to the observed dataset minimum and maximum. Readings hold state across iterations; tool wear accumulates rather than being generated independently.

- `normal`: small variations around telemetry medians.
- `degradation`: gradually increases tool wear and moves torque/RPM toward high-load and low-speed empirical percentiles.
- `high_torque`: gradually moves torque upward and RPM downward using the observed torque/RPM relationship.
- `overheating`: gradually moves both temperatures toward their upper empirical percentiles.
- `failure`: combines abnormal temperature, torque, wear, and RPM trajectories.

The scenarios do not set Target, Failure Type, condition, or risk. The existing Decision Tree model determines every returned prediction. A scenario may remain Normal for early readings, and this is reported rather than overridden.

## Run

Start the Flask backend and register/login a user first. From `backend/`:

```powershell
python -m simulator.cnc_simulator --machine CNC-LATHE-01 --interval 5 --scenario normal --username your_username --password your_password
```

For finite test runs, add `--readings 5`. Valid scenarios: `normal`, `degradation`, `high_torque`, `overheating`, and `failure`.

The React dashboard polls the existing `GET /api/machines/<machineId>` route every five seconds. The Live CNC Lathe Telemetry section initially monitors `CNC-LATHE-01`; enter another simulator machine identifier to follow it.
