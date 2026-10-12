
from pathlib import Path

import joblib
import pandas as pd

from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix
)

from ml.feature_engineering import FEATURE_COLUMNS


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = PROJECT_ROOT / "ml" / "data" / "processed" / "training_data.csv"
MODEL_DIR = PROJECT_ROOT / "ml" / "models"
MODEL_PATH = MODEL_DIR / "struggle_model.joblib"

TARGET_COLUMN = "struggle_level"


def train_model():
    """
    Train a struggle-level classifier using labelled data.

    The CSV must contain FEATURE_COLUMNS and a struggle_level
    column with Low, Moderate, or High labels.
    """

    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Training dataset not found: {DATA_PATH}\n"
            "Create ml/data/processed/training_data.csv first."
        )

    df = pd.read_csv(DATA_PATH)

    required_columns = FEATURE_COLUMNS + [TARGET_COLUMN]
    missing_columns = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Dataset is missing columns: {missing_columns}"
        )

    df = df[required_columns].copy()
    df = df.dropna(subset=[TARGET_COLUMN])

    if df.empty:
        raise ValueError("No labelled training records were found")

    X = df[FEATURE_COLUMNS].apply(
        pd.to_numeric, errors="coerce"
    )
    X = X.replace([float("inf"), float("-inf")], float("nan"))

    y = df[TARGET_COLUMN].astype(str).str.strip().str.title()

    allowed_labels = {"Low", "Moderate", "High"}
    invalid_labels = sorted(set(y) - allowed_labels)

    if invalid_labels:
        raise ValueError(
            f"Invalid struggle labels: {invalid_labels}. "
            "Use Low, Moderate, or High."
        )

    if y.nunique() < 2:
        raise ValueError(
            "Training requires at least two different struggle labels."
        )

    # Stratification requires at least two examples per class.
    class_counts = y.value_counts()

    if class_counts.min() < 2:
        raise ValueError(
            "Each struggle level needs at least two labelled examples "
            "for this train/test split. Collect more labelled data first."
        )

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.25,
        random_state=42,
        stratify=y
    )

    # Keep preprocessing inside the pipeline to prevent data leakage.
    model = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("classifier", RandomForestClassifier(
            n_estimators=100,
            random_state=42,
            class_weight="balanced"
        ))
    ])

    model.fit(X_train, y_train)

    predictions = model.predict(X_test)

    print("Model evaluation")
    print("----------------")
    print("Test accuracy:", round(
        accuracy_score(y_test, predictions), 3
    ))
    print("\nClassification report:")
    print(classification_report(
        y_test,
        predictions,
        labels=["Low", "Moderate", "High"],
        zero_division=0
    ))
    print("Confusion matrix (Low, Moderate, High):")
    print(confusion_matrix(
        y_test,
        predictions,
        labels=["Low", "Moderate", "High"]
    ))

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)

    print(f"\nModel saved to: {MODEL_PATH}")

    return model


if __name__ == "__main__":
    train_model()
