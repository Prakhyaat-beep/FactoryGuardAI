"""Load the saved model for future Flask prediction endpoints."""

from pathlib import Path
import joblib

MODEL_PATH = Path(__file__).resolve().parents[1] / "model" / "failure_model.joblib"


def load_trained_model():
    """Load the complete preprocessing-and-classification pipeline."""
    if not MODEL_PATH.exists():
        raise FileNotFoundError("Trained model not found. Run `python -m ml.train` from backend first.")
    return joblib.load(MODEL_PATH)
