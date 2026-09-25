"""Feature selection and preprocessing pipeline construction."""

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

TARGET_COLUMN = "Machine failure"
NUMERIC_FEATURES = ["Air temperature [K]", "Process temperature [K]", "Rotational speed [rpm]", "Torque [Nm]", "Tool wear [min]"]
CATEGORICAL_FEATURES = ["Type"]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES


def prepare_features_and_target(dataframe):
    """Validate source data and return selected features plus the failure target."""
    required = set(FEATURES + [TARGET_COLUMN])
    missing = required.difference(dataframe.columns)
    if missing:
        raise ValueError(f"Dataset is missing required columns: {sorted(missing)}")
    features = dataframe[FEATURES].copy()
    target = dataframe[TARGET_COLUMN].copy()
    if not target.isin([0, 1]).all():
        raise ValueError("Machine failure target must contain only 0 and 1.")
    return features, target


def build_preprocessor():
    """Create a preprocessor to be fitted on training data by a Pipeline."""
    numeric = Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())])
    categorical = Pipeline([("imputer", SimpleImputer(strategy="most_frequent")), ("one_hot", OneHotEncoder(handle_unknown="ignore"))])
    return ColumnTransformer([
        ("numeric", numeric, NUMERIC_FEATURES),
        ("categorical", categorical, CATEGORICAL_FEATURES),
    ])
