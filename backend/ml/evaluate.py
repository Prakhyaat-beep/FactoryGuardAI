from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score


def evaluate_model(target, predictions, inference_seconds, probabilities=None):
    """Calculate metrics with failure (1) as the positive class, including ROC-AUC where supported."""
    roc_auc = None
    if probabilities is not None:
        try:
            roc_auc = round(float(roc_auc_score(target, probabilities)), 4)
        except Exception:
            roc_auc = None

    return {
        "accuracy": round(float(accuracy_score(target, predictions)), 4),
        "precision": round(float(precision_score(target, predictions, zero_division=0)), 4),
        "recall": round(float(recall_score(target, predictions, zero_division=0)), 4),
        "f1_score": round(float(f1_score(target, predictions, zero_division=0)), 4),
        "roc_auc": roc_auc,
        "confusion_matrix": confusion_matrix(target, predictions, labels=[0, 1]).tolist(),
        "inference_time_ms": round(inference_seconds * 1000, 3),
        "inference_time_per_record_ms": round((inference_seconds * 1000) / len(target), 6),
    }

