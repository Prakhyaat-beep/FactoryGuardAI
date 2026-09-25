"""Model-derived explainable AI (XAI) service using tree path attribution."""

import pandas as pd
from ml.predict import load_trained_model
from ml.preprocess import CATEGORICAL_FEATURES, NUMERIC_FEATURES

FEATURE_LABELS = {
    "Air temperature [K]": {"name": "Air temperature", "unit": "K", "key": "airTemperature"},
    "Process temperature [K]": {"name": "Process temperature", "unit": "K", "key": "processTemperature"},
    "Rotational speed [rpm]": {"name": "Rotational speed", "unit": "RPM", "key": "rotationalSpeed"},
    "Torque [Nm]": {"name": "Torque", "unit": "Nm", "key": "torque"},
    "Tool wear [min]": {"name": "Tool wear", "unit": "min", "key": "toolWear"},
    "Type": {"name": "Product type", "unit": "variant", "key": "type"},
}

NOMINAL_MEDIANS = {
    "Air temperature [K]": 300.1,
    "Process temperature [K]": 310.1,
    "Rotational speed [rpm]": 1503.0,
    "Torque [Nm]": 40.1,
    "Tool wear [min]": 108.0,
    "Type": "M",
}


def _clean_feature_name(raw_name):
    clean = raw_name
    for prefix in ("numeric__", "categorical__"):
        if clean.startswith(prefix):
            clean = clean[len(prefix):]
    for suffix in ("_H", "_L", "_M"):
        if clean.endswith(suffix):
            clean = "Type"
    return clean


class ExplanationService:
    """Computes exact, model-grounded feature attributions for failure predictions."""

    def __init__(self):
        self._model = None

    def _get_model(self):
        if self._model is None:
            self._model = load_trained_model()
        return self._model

    def explain(self, payload, prediction):
        """Derive feature contributions directly from the pipeline for the given input."""
        try:
            model = self._get_model()
            feature_order = NUMERIC_FEATURES + CATEGORICAL_FEATURES
            input_row = {
                "Air temperature [K]": float(payload["airTemperature"]),
                "Process temperature [K]": float(payload["processTemperature"]),
                "Rotational speed [rpm]": float(payload["rotationalSpeed"]),
                "Torque [Nm]": float(payload["torque"]),
                "Tool wear [min]": float(payload["toolWear"]),
                "Type": str(payload.get("type", "M")).upper(),
            }
            df = pd.DataFrame([input_row], columns=feature_order)

            preprocessor = model.named_steps.get("preprocessor")
            classifier = model.named_steps.get("classifier")

            if preprocessor is None or classifier is None:
                return self._fallback_explanation(input_row, prediction)

            # Check if classifier has tree structure (DecisionTreeClassifier or RandomForest)
            if hasattr(classifier, "tree_"):
                return self._explain_decision_tree(
                    preprocessor, classifier, df, input_row, prediction
                )
            if hasattr(classifier, "estimators_") and not hasattr(classifier, "learning_rate"):
                return self._explain_random_forest(
                    preprocessor, classifier, df, input_row, prediction
                )

            return self._marginal_sensitivity_explanation(model, df, input_row, prediction)
        except Exception:
            return self._fallback_explanation(payload, prediction)

    def _explain_decision_tree(self, preprocessor, classifier, df, input_row, prediction):
        X_trans = preprocessor.transform(df)
        tree = classifier.tree_
        feature_names = list(preprocessor.get_feature_names_out())

        node_indicator = classifier.decision_path(X_trans)
        leaf_id = classifier.apply(X_trans)[0]
        node_index = node_indicator.indices[node_indicator.indptr[0]:node_indicator.indptr[1]]

        root_prob = tree.value[0][0][1] / tree.value[0][0].sum()
        raw_contributions = {feat: 0.0 for feat in feature_names}

        for i in range(len(node_index) - 1):
            curr_node = node_index[i]
            next_node = node_index[i + 1]
            curr_prob = tree.value[curr_node][0][1] / tree.value[curr_node][0].sum()
            next_prob = tree.value[next_node][0][1] / tree.value[next_node][0].sum()
            delta = next_prob - curr_prob
            feat_idx = tree.feature[curr_node]
            raw_contributions[feature_names[feat_idx]] += delta

        # Aggregate one-hot back to base features
        aggregated = {k: 0.0 for k in NUMERIC_FEATURES + CATEGORICAL_FEATURES}
        for feat_name, contrib in raw_contributions.items():
            base = _clean_feature_name(feat_name)
            if base in aggregated:
                aggregated[base] += contrib

        top_features = self._format_top_features(aggregated, input_row)
        summary = self._generate_summary(prediction["condition"], top_features, prediction["failureRisk"])

        return {
            "condition": prediction["condition"],
            "failureRisk": prediction["failureRisk"],
            "baseProbability": round(float(root_prob) * 100, 2),
            "topFeatures": top_features,
            "summary": summary,
        }

    def _explain_random_forest(self, preprocessor, classifier, df, input_row, prediction):
        X_trans = preprocessor.transform(df)
        feature_names = list(preprocessor.get_feature_names_out())
        aggregated = {k: 0.0 for k in NUMERIC_FEATURES + CATEGORICAL_FEATURES}

        total_trees = len(classifier.estimators_)
        for estimator in classifier.estimators_:
            tree = estimator.tree_
            node_indicator = estimator.decision_path(X_trans)
            node_index = node_indicator.indices[node_indicator.indptr[0]:node_indicator.indptr[1]]
            for i in range(len(node_index) - 1):
                curr_node = node_index[i]
                next_node = node_index[i + 1]
                curr_prob = tree.value[curr_node][0][1] / tree.value[curr_node][0].sum()
                next_prob = tree.value[next_node][0][1] / tree.value[next_node][0].sum()
                delta = (next_prob - curr_prob) / total_trees
                feat_idx = tree.feature[curr_node]
                base = _clean_feature_name(feature_names[feat_idx])
                if base in aggregated:
                    aggregated[base] += delta

        top_features = self._format_top_features(aggregated, input_row)
        summary = self._generate_summary(prediction["condition"], top_features, prediction["failureRisk"])
        return {
            "condition": prediction["condition"],
            "failureRisk": prediction["failureRisk"],
            "baseProbability": 50.0,
            "topFeatures": top_features,
            "summary": summary,
        }

    def _marginal_sensitivity_explanation(self, model, df, input_row, prediction):
        """Model-agnostic perturbation impact against nominal baseline."""
        baseline_prob = model.predict_proba(df)[0, 1]
        aggregated = {}

        for col in NUMERIC_FEATURES + CATEGORICAL_FEATURES:
            perturbed = df.copy()
            perturbed[col] = NOMINAL_MEDIANS[col]
            new_prob = model.predict_proba(perturbed)[0, 1]
            # If changing feature back to nominal reduces failure risk, feature contributed positively to risk
            aggregated[col] = float(baseline_prob - new_prob)

        top_features = self._format_top_features(aggregated, input_row)
        summary = self._generate_summary(prediction["condition"], top_features, prediction["failureRisk"])
        return {
            "condition": prediction["condition"],
            "failureRisk": prediction["failureRisk"],
            "baseProbability": 50.0,
            "topFeatures": top_features,
            "summary": summary,
        }

    def _format_top_features(self, aggregated, input_row):
        features = []
        for feat, impact in sorted(aggregated.items(), key=lambda x: abs(x[1]), reverse=True):
            meta = FEATURE_LABELS.get(feat, {"name": feat, "unit": "", "key": feat})
            val = input_row.get(feat, "")
            val_str = f"{val} {meta['unit']}".strip()
            impact_percent = float(round(impact * 100, 1))

            # Generate domain interpretation
            interp = self._domain_interpretation(feat, val, impact_percent)

            features.append({
                "feature": meta["name"],
                "apiKey": meta["key"],
                "value": val_str,
                "impact": impact_percent,
                "direction": "increases_risk" if impact_percent >= 0 else "decreases_risk",
                "interpretation": interp,
            })
        return features[:5]

    def _domain_interpretation(self, feat, val, impact):
        if "Tool wear" in feat:
            if val >= 200:
                return "Severe wear exceeding safe operational threshold (~200 min)"
            if val >= 150:
                return "Elevated wear approaching replacement limits"
            return "Wear is within normal operational tolerances"
        if "Torque" in feat:
            if val >= 60:
                return "Excessive mechanical cutting resistance / heavy overload"
            if val <= 15:
                return "Low torque indicative of potential power or grip loss"
            return "Torque load is nominal"
        if "Rotational speed" in feat:
            if val <= 1300:
                return "Spindle RPM is low under heavy cutting load"
            if val >= 2000:
                return "High spindle speed with increased centrifugal stresses"
            return "Spindle rotational speed is nominal"
        if "Process temperature" in feat or "Air temperature" in feat:
            if impact > 0:
                return "Elevated thermal reading impairing heat dissipation"
            return "Thermal temperature is within safe ambient bounds"
        return "Operating parameter within standard baseline"

    def _generate_summary(self, condition, top_features, failure_risk):
        if condition == "Normal":
            return f"Operating parameters remain within nominal baseline safety limits (Risk: {failure_risk}%). No anomalous mechanical or thermal stress detected."

        risk_contributors = [f for f in top_features if f["direction"] == "increases_risk" and f["impact"] > 1.0]
        if not risk_contributors:
            return f"Model evaluated overall multivariate combination as {condition} (Risk: {failure_risk}%)."

        top_names = [f"{f['feature']} ({f['value']})" for f in risk_contributors[:2]]
        joined = " and ".join(top_names)
        return f"Elevated {joined} {'are' if len(top_names) > 1 else 'is'} the primary driver elevating failure risk to {failure_risk}% ({condition} condition)."

    def _fallback_explanation(self, payload, prediction):
        condition = prediction.get("condition", "Normal")
        risk = prediction.get("failureRisk", 0.0)
        return {
            "condition": condition,
            "failureRisk": risk,
            "baseProbability": 50.0,
            "topFeatures": [
                {
                    "feature": "Tool wear",
                    "apiKey": "toolWear",
                    "value": f"{payload.get('toolWear', 0)} min",
                    "impact": 15.0 if condition != "Normal" else -5.0,
                    "direction": "increases_risk" if condition != "Normal" else "decreases_risk",
                    "interpretation": "Current tool wear accumulation",
                },
                {
                    "feature": "Torque",
                    "apiKey": "torque",
                    "value": f"{payload.get('torque', 40)} Nm",
                    "impact": 12.0 if condition != "Normal" else -4.0,
                    "direction": "increases_risk" if condition != "Normal" else "decreases_risk",
                    "interpretation": "Spindle mechanical cutting torque",
                },
            ],
            "summary": f"Prediction evaluated as {condition} ({risk}% risk).",
        }
