
from sklearn.base import clone
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedGroupKFold
import joblib

from ml.codestream_features import build_codestream_dataset


MODEL_PATH = "ml/models/codestream_verdict_model.joblib"
TARGET = "is_unsuccessful"

CODE_FEATURES = [
    "source_code_missing",
    "code_length_chars",
    "code_length_non_whitespace",
    "code_total_lines",
    "code_nonempty_lines",
    "programming_language",
]

def main():
    artifact = joblib.load(MODEL_PATH)
    combined_model = artifact["model"]
    all_features = artifact["features"]

    df = build_codestream_dataset()
    y = df[TARGET].astype(int)
    groups = df["user_id"]

    code_features = [f for f in CODE_FEATURES if f in all_features]
    history_features = [f for f in all_features if f not in code_features]

    experiments = {
        "Code only": code_features,
        "Combined": all_features,
    }

    cv = StratifiedGroupKFold(
        n_splits=5, shuffle=True, random_state=42
    )

    scores = {name: [] for name in experiments}

    for fold, (train_idx, test_idx) in enumerate(
        cv.split(df[all_features], y, groups), start=1
    ):
        train_users = set(groups.iloc[train_idx])
        test_users = set(groups.iloc[test_idx])
        assert train_users.isdisjoint(test_users)

        for name, features in experiments.items():
            X_train = df.iloc[train_idx][features]
            X_test = df.iloc[test_idx][features]
            y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

            # Reuse the trained pipeline's preprocessing and classifier,
            # selecting only the feature columns for this experiment.
            if name == "Combined":
                model = clone(combined_model)
            else:
                from ml.train_codestream import make_preprocessor, NUMERIC_FEATURES, CATEGORICAL_FEATURES
                from sklearn.pipeline import Pipeline
                from sklearn.ensemble import RandomForestClassifier

                numeric = [f for f in features if f in NUMERIC_FEATURES]
                categorical = [f for f in features if f in CATEGORICAL_FEATURES]

                from sklearn.compose import ColumnTransformer
                preprocessor = ColumnTransformer([
                    ("numeric", make_preprocessor().transformers[0][1], numeric),
                    ("categorical", make_preprocessor().transformers[1][1], categorical),
                ])

                model = Pipeline([
                    ("preprocessor", preprocessor),
                    ("classifier", RandomForestClassifier(
                        n_estimators=300,
                        min_samples_leaf=2,
                        class_weight="balanced",
                        random_state=42,
                        n_jobs=-1,
                    )),
                ])

            model.fit(X_train, y_train)
            pred = model.predict(X_test)
            prob = model.predict_proba(X_test)[:, 1]

            scores[name].append([
                accuracy_score(y_test, pred),
                balanced_accuracy_score(y_test, pred),
                f1_score(y_test, pred, zero_division=0),
                roc_auc_score(y_test, prob),
            ])

        print(f"Fold {fold}: train users={len(train_users)}, test users={len(test_users)}")

    print("\nMean results across 5 folds")
    for name, rows in scores.items():
        print(f"\n{name}")
        for i, metric in enumerate([
            "Accuracy", "Balanced accuracy", "F1 (Unsuccessful)", "ROC-AUC"
        ]):
            print(f"{metric}: {sum(r[i] for r in rows) / len(rows):.4f}")


if __name__ == "__main__":
    main()
