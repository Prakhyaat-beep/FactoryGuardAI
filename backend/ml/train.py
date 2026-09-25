"""Train, evaluate, and save FactoryGuard's baseline ML models."""

import json
import time
from pathlib import Path

import joblib
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier

from ml.data_loader import load_dataset
from ml.evaluate import evaluate_model
from ml.preprocess import build_preprocessor, prepare_features_and_target

RANDOM_STATE = 42
TEST_SIZE = 0.2
MODEL_DIR = Path(__file__).resolve().parents[1] / "model"
MODEL_PATH = MODEL_DIR / "failure_model.joblib"
EVALUATION_PATH = MODEL_DIR / "evaluation_results.json"


def build_models():
    return {
        "logistic_regression": LogisticRegression(max_iter=1000, class_weight="balanced", random_state=RANDOM_STATE),
        "decision_tree": DecisionTreeClassifier(class_weight="balanced", random_state=RANDOM_STATE, min_samples_leaf=2),
        "random_forest": RandomForestClassifier(n_estimators=200, class_weight="balanced", random_state=RANDOM_STATE, n_jobs=1),
        "svm": SVC(probability=True, class_weight="balanced", random_state=RANDOM_STATE),
        "gradient_boosting": GradientBoostingClassifier(n_estimators=100, random_state=RANDOM_STATE),
    }


def train_and_save():
    """Run the pipeline for all 5 models and save the best held-out F1 model."""
    raw_data = load_dataset()
    features, target = prepare_features_and_target(raw_data)
    x_train, x_test, y_train, y_test = train_test_split(
        features, target, test_size=TEST_SIZE, stratify=target, random_state=RANDOM_STATE
    )
    results, trained_pipelines = {}, {}
    for model_name, classifier in build_models().items():
        pipeline = Pipeline([("preprocessor", build_preprocessor()), ("classifier", classifier)])
        training_start = time.perf_counter()
        pipeline.fit(x_train, y_train)
        training_seconds = time.perf_counter() - training_start
        inference_start = time.perf_counter()
        predictions = pipeline.predict(x_test)
        inference_seconds = time.perf_counter() - inference_start

        probabilities = None
        if hasattr(pipeline, "predict_proba"):
            try:
                probabilities = pipeline.predict_proba(x_test)[:, 1]
            except Exception:
                probabilities = None

        results[model_name] = evaluate_model(y_test, predictions, inference_seconds, probabilities=probabilities)
        results[model_name]["training_time_seconds"] = round(training_seconds, 4)
        trained_pipelines[model_name] = pipeline

    selected_model_name = max(results, key=lambda name: results[name]["f1_score"])
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(trained_pipelines[selected_model_name], MODEL_PATH)
    evaluation_output = {
        "dataset": "AI4I 2020 Predictive Maintenance Dataset (supplied CSV when available)",
        "target": "Machine failure",
        "features": list(features.columns),
        "random_state": RANDOM_STATE,
        "test_size": TEST_SIZE,
        "train_rows": int(len(x_train)),
        "test_rows": int(len(x_test)),
        "failure_rate": round(float(target.mean()), 4),
        "selection_metric": "f1_score for machine failure class (1)",
        "selected_model": selected_model_name,
        "models": results,
    }
    EVALUATION_PATH.write_text(json.dumps(evaluation_output, indent=2), encoding="utf-8")
    return evaluation_output


if __name__ == "__main__":
    print(json.dumps(train_and_save(), indent=2))
