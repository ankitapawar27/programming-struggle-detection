
from pathlib import Path

import joblib
import pandas as pd

from ml.feature_engineering import FEATURE_COLUMNS


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = PROJECT_ROOT / "ml" / "models" / "struggle_model.joblib"


def predict_struggle(features):
    """
    Predict a struggle level from a dictionary of behaviour features.

    This model was trained on synthetic demonstration data.
    Its predictions are for pipeline testing only, not validated
    assessments of real students.
    """

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Trained model not found: {MODEL_PATH}. "
            "Run python -m ml.train first."
        )

    if not isinstance(features, dict):
        raise ValueError("features must be a dictionary")

    missing_columns = [
        column for column in FEATURE_COLUMNS
        if column not in features
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required features: {missing_columns}"
        )

    # Arrange the input in the same order used during training
    input_df = pd.DataFrame(
        [[features[column] for column in FEATURE_COLUMNS]],
        columns=FEATURE_COLUMNS
    )

    for column in FEATURE_COLUMNS:
        input_df[column] = pd.to_numeric(
            input_df[column], errors="raise"
        )

    if input_df.isnull().any().any():
        raise ValueError("Feature values cannot be missing")

    model = joblib.load(MODEL_PATH)
    prediction = model.predict(input_df)[0]

    probabilities = model.predict_proba(input_df)[0]
    classes = model.named_steps["classifier"].classes_

    confidence = {
        str(label): round(float(probability), 4)
        for label, probability in zip(classes, probabilities)
    }

    return {
        "struggle_level": str(prediction),
        "class_probabilities": confidence,
        "model_type": "synthetic_demo_only"
    }


if __name__ == "__main__":
    sample_features = {
        "attempt_number": 2,
        "error_count": 1,
        "execution_count": 3,
        "time_spent_seconds": 120,
        "total_events": 4,
        "execution_events": 3,
        "error_events": 1,
        "submission_events": 1
    }

    result = predict_struggle(sample_features)

    print("Prediction result:")
    print(result)
