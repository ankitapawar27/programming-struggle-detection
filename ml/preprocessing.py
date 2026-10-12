
import pandas as pd

from sklearn.impute import SimpleImputer

from ml.feature_engineering import FEATURE_COLUMNS


def preprocess_features(df):
    """
    Validate and preprocess numerical features for ML.

    Returns a DataFrame containing the eight model features.
    """

    if df is None or df.empty:
        raise ValueError("The input dataset is empty")

    missing_columns = [
        column for column in FEATURE_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required feature columns: {missing_columns}"
        )

    # Select only the features used by the model
    X = df[FEATURE_COLUMNS].copy()

    # Convert values to numeric; invalid values become missing
    for column in FEATURE_COLUMNS:
        X[column] = pd.to_numeric(
            X[column], errors="coerce"
        )

    # Replace infinite values with missing values
    X = X.replace([float("inf"), float("-inf")], float("nan"))

    # Fill missing values using the median of each feature
    imputer = SimpleImputer(strategy="median")
    processed_values = imputer.fit_transform(X)

    processed_df = pd.DataFrame(
        processed_values,
        columns=FEATURE_COLUMNS,
        index=X.index
    )

    return processed_df


def load_feature_dataset(submission_ids):
    """
    Extract features from MySQL and preprocess them.
    """

    from ml.feature_engineering import prepare_feature_data

    raw_df = prepare_feature_data(submission_ids)
    X = preprocess_features(raw_df)

    return X
