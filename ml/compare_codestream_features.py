
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
    roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from ml.codestream_features import build_codestream_dataset


TARGET = "is_unsuccessful"
GROUP = "user_id"

HISTORY = [
    "attempt_number",
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

CODE_NUMERIC = [
    "source_code_missing",
    "code_length_chars",
    "code_length_non_whitespace",
    "code_total_lines",
    "code_nonempty_lines",
]

CATEGORICAL = ["programming_language"]

EXPERIMENTS = {
    "History only": HISTORY,
    "Code only": CODE_NUMERIC + CATEGORICAL,
    "Combined": HISTORY + CODE_NUMERIC + CATEGORICAL,
}


def build_model(features):
    numeric = [c for c in features if c != "programming_language"]
    categorical = [c for c in features if c == "programming_language"]

    transformers = []

    if numeric:
        numeric_pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ])
        transformers.append(("numeric", numeric_pipeline, numeric))

    if categorical:
        categorical_pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", OneHotEncoder(handle_unknown="ignore")),
        ])
        transformers.append(
            ("categorical", categorical_pipeline, categorical)
        )

    return Pipeline([
        ("preprocessor", ColumnTransformer(transformers)),
        ("classifier", RandomForestClassifier(
            n_estimators=300,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )),
    ])


def main():
    df = build_codestream_dataset()

    splitter = GroupShuffleSplit(
        n_splits=1,
        test_size=0.25,
        random_state=42,
    )

    train_idx, test_idx = next(
        splitter.split(df, df[TARGET], groups=df[GROUP])
    )

    train_users = set(df.iloc[train_idx][GROUP])
    test_users = set(df.iloc[test_idx][GROUP])

    assert train_users.isdisjoint(test_users)

    train = df.iloc[train_idx]
    test = df.iloc[test_idx]

    print("Fixed user-grouped holdout")
    print("Training rows:", len(train))
    print("Testing rows:", len(test))
    print("Training users:", len(train_users))
    print("Testing users:", len(test_users))
    print("\nResults (same split for every experiment)")

    for name, features in EXPERIMENTS.items():
        model = build_model(features)

        model.fit(train[features], train[TARGET])

        predictions = model.predict(test[features])
        probabilities = model.predict_proba(test[features])[:, 1]

        print(f"\n{name}")
        print("-" * len(name))
        print("Accuracy:", round(
            accuracy_score(test[TARGET], predictions), 4
        ))
        print("Balanced accuracy:", round(
            balanced_accuracy_score(test[TARGET], predictions), 4
        ))
        print("Macro F1:", round(
            f1_score(test[TARGET], predictions, average="macro"), 4
        ))
        print("Unsuccessful recall:", round(
            (predictions[test[TARGET].to_numpy() == 1] == 1).mean()
            if (test[TARGET] == 1).any() else 0,
            4,
        ))
        print("ROC-AUC:", round(
            roc_auc_score(test[TARGET], probabilities), 4
        ))

    print("\nComparison complete. No model files were saved.")


if __name__ == "__main__":
    main()

