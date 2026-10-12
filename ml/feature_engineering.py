
import pandas as pd

from backend.services.feature_extractor import extract_features


# Features used by the machine-learning model
FEATURE_COLUMNS = [
    "attempt_number",
    "error_count",
    "execution_count",
    "time_spent_seconds",
    "total_events",
    "execution_events",
    "error_events",
    "submission_events"
]


def prepare_feature_data(submission_ids):
    """
    Extract features for multiple submissions and return
    a Pandas DataFrame ready for ML preprocessing.
    """

    if not submission_ids:
        raise ValueError("At least one submission ID is required")

    records = []

    for submission_id in submission_ids:
        features = extract_features(submission_id)
        records.append(features)

    df = pd.DataFrame(records)

    # Ensure all required feature columns are present
    for column in FEATURE_COLUMNS:
        if column not in df.columns:
            df[column] = 0

    # Convert features to numeric values
    for column in FEATURE_COLUMNS:
        df[column] = pd.to_numeric(
            df[column], errors="coerce"
        )

    # Replace missing feature values with zero
    df[FEATURE_COLUMNS] = (
        df[FEATURE_COLUMNS]
        .fillna(0)
        .astype(float)
    )

    return df


def get_model_features(df):
    """
    Return only the feature columns expected by the model.
    """

    missing_columns = [
        column for column in FEATURE_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    return df[FEATURE_COLUMNS].copy()
