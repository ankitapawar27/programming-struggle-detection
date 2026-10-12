
from pathlib import Path

import joblib
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from ml.codestream_features import build_codestream_dataset


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = PROJECT_ROOT / "ml" / "models"
MODEL_PATH = MODEL_DIR / "codestream_verdict_model.joblib"

TARGET = "is_unsuccessful"
GROUP = "user_id"

NUMERIC_FEATURES = [
    "attempt_number",
    "source_code_missing",
    "code_length_chars",
    "code_length_non_whitespace",
    "code_total_lines",
    "code_nonempty_lines",
    "previous_observed_submissions",
    "previous_unsuccessful_submissions",
    "previous_accepted_submissions",
    "previous_wrong_answers",
    "previous_compilation_errors",
    "previous_runtime_errors",
    "previous_presentation_errors",
    "previous_time_limit_exceeded",
    "unobserved_attempt_numbers_before_current",
]

CATEGORICAL_FEATURES = ["programming_language"]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES


def make_preprocessor():
    """Fit preprocessing only on the training partition."""

    numeric_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])

    categorical_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("encoder", OneHotEncoder(handle_unknown="ignore")),
    ])

    return ColumnTransformer([
        ("numeric", numeric_pipeline, NUMERIC_FEATURES),
        ("categorical", categorical_pipeline, CATEGORICAL_FEATURES),
    ])


def report_metrics(name, y_true, predictions, probabilities):
    """Print useful binary-classification metrics."""

    print(f"\n{name}")
    print("-" * len(name))
    print("Accuracy:", round(accuracy_score(y_true, predictions), 4))
    print(
        "Balanced accuracy:",
        round(balanced_accuracy_score(y_true, predictions), 4),
    )
    print(
        "Unsuccessful precision:",
        round(precision_score(y_true, predictions, zero_division=0), 4),
    )
    print(
        "Unsuccessful recall:",
        round(recall_score(y_true, predictions, zero_division=0), 4),
    )
    print(
        "Unsuccessful F1:",
        round(f1_score(y_true, predictions, zero_division=0), 4),
    )

    print("\nClassification report:")
    print(classification_report(
        y_true,
        predictions,
        labels=[0, 1],
        target_names=["Accepted", "Unsuccessful"],
        zero_division=0,
    ))

    print("Confusion matrix (rows=actual, columns=predicted):")
    print(confusion_matrix(y_true, predictions, labels=[0, 1]))

    if len(set(y_true)) == 2:
        print(
            "ROC-AUC:",
            round(roc_auc_score(y_true, probabilities), 4),
        )


def train_codestream_model():
    print("Loading real CodeStream data...")
    df = build_codestream_dataset()

    required = FEATURES + [TARGET, GROUP]
    missing = [column for column in required if column not in df.columns]

    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    X = df[FEATURES].copy()
    y = df[TARGET].astype(int)
    groups = df[GROUP]

    if y.nunique() != 2:
        raise ValueError("Both target classes must be present.")

    # Hold out entire users; never split a user's submissions across sets.
    splitter = GroupShuffleSplit(
        n_splits=1,
        test_size=0.25,
        random_state=42,
    )

    train_indices, test_indices = next(
        splitter.split(X, y, groups=groups)
    )

    X_train = X.iloc[train_indices].copy()
    X_test = X.iloc[test_indices].copy()
    y_train = y.iloc[train_indices].copy()
    y_test = y.iloc[test_indices].copy()

    train_users = set(groups.iloc[train_indices])
    test_users = set(groups.iloc[test_indices])

    if train_users & test_users:
        raise RuntimeError("User leakage detected in train/test split.")

    if y_train.nunique() != 2 or y_test.nunique() != 2:
        raise ValueError(
            "A split contains only one target class. "
            "Review the split before training."
        )

    print("\nDataset summary")
    print("----------------")
    print("Total submissions:", len(df))
    print("Training submissions:", len(train_indices))
    print("Testing submissions:", len(test_indices))
    print("Training users:", len(train_users))
    print("Testing users:", len(test_users))
    print("Target distribution (0=Accepted, 1=Unsuccessful):")
    print(y.value_counts().sort_index().to_dict())
    print("Training target distribution:")
    print(y_train.value_counts().sort_index().to_dict())
    print("Testing target distribution:")
    print(y_test.value_counts().sort_index().to_dict())
    print("Users shared across splits:", len(train_users & test_users))

    # Majority-class baseline. It learns from training data only.
    baseline = DummyClassifier(strategy="most_frequent")
    baseline.fit(X_train, y_train)
    baseline_predictions = baseline.predict(X_test)
    baseline_probabilities = baseline.predict_proba(X_test)[:, 1]

    report_metrics(
        "Majority-class baseline",
        y_test,
        baseline_predictions,
        baseline_probabilities,
    )

    model = Pipeline([
        ("preprocessor", make_preprocessor()),
        ("classifier", RandomForestClassifier(
            n_estimators=300,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )),
    ])

    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    probabilities = model.predict_proba(X_test)[:, 1]

    report_metrics(
        "CodeStream Random Forest",
        y_test,
        predictions,
        probabilities,
    )

    # Save only after evaluation completes.
    # This is an experimental verdict-prediction model, not a
    # validated psychological struggle detector.
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    artifact = {
        "model": model,
        "features": FEATURES,
        "target": TARGET,
        "target_mapping": {
            0: "Accepted",
            1: "Unsuccessful",
        },
        "model_type": "codestream_submission_verdict_experiment",
        "evaluation_split": "user_grouped_holdout",
        "random_state": 42,
    }

    joblib.dump(artifact, MODEL_PATH)
    print(f"\nExperimental model saved to: {MODEL_PATH}")
    print("Interpretation: predicts submission verdict category,")
    print("not verified student struggle.")


if __name__ == "__main__":
    train_codestream_model()
