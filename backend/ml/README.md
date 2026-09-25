# FactoryGuard ML foundation

## Dataset

The pipeline uses the **AI4I 2020 Predictive Maintenance Dataset**, published by the [UCI Machine Learning Repository](https://archive.ics.uci.edu/dataset/601/ai4i+2020+predictive+maintenance+dataset) under CC BY 4.0. It has 10,000 synthetic-but-industry-representative records. The supplied `backend/data/predictive_maintenance.csv` is preferred when available; it uses `Target`, which the loader normalizes to the existing `Machine failure` target name. Otherwise, the training command downloads UCI's published archive to `backend/data/ai4i2020.csv`.

## Features and target

The target is `Machine failure`: `0` for no failure and `1` for failure.

| Dataset feature | FactoryGuard interpretation |
| --- | --- |
| Air temperature [K] | Ambient operating temperature |
| Process temperature [K] | Machine/process temperature |
| Rotational speed [rpm] | Machine speed |
| Torque [Nm] | Mechanical load proxy |
| Tool wear [min] | Component-health/wear indicator |
| Type | Product quality category |

AI4I has no direct vibration, electrical-current, or pressure reading. Torque is the available load-related proxy. `UDI`, `Product ID`, `Failure Type`, and individual failure-mode columns are not model inputs; using failure labels or failure modes would leak the answer into the model.

## Preprocessing and models

Data are split into stratified train/test sets before preprocessing. A scikit-learn Pipeline fits median imputation and standard scaling for numerical data, plus most-frequent imputation and one-hot encoding for `Type`, using training rows only.

Baseline models are Logistic Regression, Decision Tree, and Random Forest. Each uses `random_state=42`; class balancing accounts for uncommon failures.

## Evaluation and selection

Each model records accuracy, precision, recall, F1-score, and a `[ [TN, FP], [FN, TP] ]` confusion matrix on held-out test rows. The primary model is selected by failure-class F1, not accuracy alone. Actual results are written to `backend/model/evaluation_results.json` after training.

With the reproducible split used in this project (80% training / 20% testing, `random_state=42`), the **Decision Tree** was selected. Its held-out failure-class precision was `0.7015`, recall `0.6912`, and F1-score `0.6963`; its accuracy was `0.9795`. These results are specific to AI4I and must not be treated as real-factory performance.

## Train from a clean state

From `backend/`:

```powershell
python -m pip install -r requirements.txt
python -m ml.train
```

This creates `backend/model/failure_model.joblib`, a loadable preprocessing-and-model pipeline, plus the evaluation JSON.

## Limitations

AI4I is synthetic, so it cannot establish performance for a real factory. It is a point-in-time binary failure classifier, not a remaining-useful-life model. Validate against representative operational data before deployment.
