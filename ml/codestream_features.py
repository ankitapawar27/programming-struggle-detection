
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = PROJECT_ROOT / "ml" / "data" / "raw"

REQUIRED_COLUMNS = [
    "submission_id",
    "user_id",
    "problem_id",
    "attempt_number",
    "source_code",
    "final_verdict",
]

UNSUCCESSFUL_VERDICTS = {
    "Wrong Answer",
    "Compilation Error",
    "Presentation Error",
    "Runtime Error",
    "Time Limit Exceeded",
    "Memory Limit Exceeded",
}


def find_submission_file():
    """Find the extracted CodeStream submission CSV."""

    matches = list(RAW_DATA_DIR.rglob("Submission Data.csv"))

    if not matches:
        raise FileNotFoundError(
            f"Submission Data.csv not found under {RAW_DATA_DIR}"
        )

    if len(matches) > 1:
        raise ValueError(
            "Multiple Submission Data.csv files found. "
            "Keep one dataset location or specify the path explicitly."
        )

    return matches[0]


def count_code_lines(source_code):
    """Count total and non-empty source-code lines."""

    if pd.isna(source_code):
        return 0, 0

    lines = str(source_code).splitlines()
    total_lines = len(lines)
    nonempty_lines = sum(bool(line.strip()) for line in lines)

    return total_lines, nonempty_lines


def build_codestream_dataset(csv_path=None):
    """
    Build one leakage-aware feature row per observed submission.

    Target:
        is_unsuccessful = 1 for an unsuccessful verdict
        is_unsuccessful = 0 for Accepted

    History features use only earlier observed submissions from
    the same user-problem pair.

    The returned DataFrame retains identifiers for grouped evaluation.
    These identifiers must not be passed to the model as features.
    """

    if csv_path is None:
        csv_path = find_submission_file()

    df = pd.read_csv(csv_path)

    missing_columns = [
        column for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Dataset is missing required columns: {missing_columns}"
        )

    # Validate essential fields.
    if df[["submission_id", "user_id", "problem_id",
           "attempt_number", "final_verdict"]].isna().any().any():
        raise ValueError(
            "Required identifiers, attempt numbers, and verdicts "
            "must not contain missing values."
        )

    df["attempt_number"] = pd.to_numeric(
        df["attempt_number"], errors="raise"
    )

    if (df["attempt_number"] < 1).any():
        raise ValueError("Attempt numbers must be positive.")

    if (df["attempt_number"] % 1 != 0).any():
        raise ValueError("Attempt numbers must be whole numbers.")

    duplicate_keys = df.duplicated(
        ["user_id", "problem_id", "attempt_number"]
    )

    if duplicate_keys.any():
        raise ValueError(
            "Duplicate user-problem-attempt combinations found."
        )

    # Normalize verdict strings and validate the target classes.
    df["final_verdict"] = (
        df["final_verdict"].astype(str).str.strip()
    )

    known_verdicts = UNSUCCESSFUL_VERDICTS | {"Accepted"}
    unknown_verdicts = sorted(
        set(df["final_verdict"]) - known_verdicts
    )

    if unknown_verdicts:
        raise ValueError(
            f"Unexpected verdict values: {unknown_verdicts}"
        )

    # Sort chronologically by the dataset's attempt index, not CSV row order.
    df = df.sort_values(
        ["user_id", "problem_id", "attempt_number"],
        kind="stable"
    ).reset_index(drop=True)

    # Current-submission code features.
    df["source_code_missing"] = (
        df["source_code"].isna().astype(int)
    )

    code = df["source_code"].fillna("").astype(str)

    df["code_length_chars"] = code.str.len()
    df["code_length_non_whitespace"] = (
        code.str.replace(r"\s+", "", regex=True).str.len()
    )

    line_counts = code.apply(count_code_lines)
    df["code_total_lines"] = line_counts.apply(lambda x: x[0])
    df["code_nonempty_lines"] = line_counts.apply(lambda x: x[1])

    # Create target from the current submission's verdict.
    df["is_unsuccessful"] = (
        df["final_verdict"].isin(UNSUCCESSFUL_VERDICTS).astype(int)
    )

    # Build features from earlier observed submissions only.
    history_records = []

    for _, group in df.groupby(
        ["user_id", "problem_id"], sort=False
    ):
        group = group.sort_values("attempt_number", kind="stable")

        observed_attempts = []

        for row in group.itertuples(index=False):
            current_attempt = int(row.attempt_number)
            previous = [
                item for item in observed_attempts
                if item["attempt_number"] < current_attempt
            ]

            previous_verdicts = [
                item["final_verdict"] for item in previous
            ]

            unsuccessful_before = sum(
                verdict in UNSUCCESSFUL_VERDICTS
                for verdict in previous_verdicts
            )

            accepted_before = sum(
                verdict == "Accepted"
                for verdict in previous_verdicts
            )

            # Count absent attempt numbers before this submission.
            # These are unobserved records, not assumed outcomes.
            observed_numbers = {
                item["attempt_number"] for item in previous
            }

            missing_before = sum(
                number not in observed_numbers
                for number in range(1, current_attempt)
            )

            history_records.append({
                "submission_id": row.submission_id,
                "previous_observed_submissions": len(previous),
                "previous_unsuccessful_submissions": unsuccessful_before,
                "previous_accepted_submissions": accepted_before,
                "previous_wrong_answers": sum(
                    v == "Wrong Answer" for v in previous_verdicts
                ),
                "previous_compilation_errors": sum(
                    v == "Compilation Error"
                    for v in previous_verdicts
                ),
                "previous_runtime_errors": sum(
                    v == "Runtime Error" for v in previous_verdicts
                ),
                "previous_presentation_errors": sum(
                    v == "Presentation Error"
                    for v in previous_verdicts
                ),
                "previous_time_limit_exceeded": sum(
                    v == "Time Limit Exceeded"
                    for v in previous_verdicts
                ),
                "unobserved_attempt_numbers_before_current": missing_before,
            })

            observed_attempts.append({
                "attempt_number": current_attempt,
                "final_verdict": row.final_verdict,
            })

    history_df = pd.DataFrame(history_records)

    result = df.merge(
        history_df,
        on="submission_id",
        how="left",
        validate="one_to_one",
    )

    # Use these identifiers for grouping and auditing only.
    metadata_columns = [
        "submission_id",
        "user_id",
        "problem_id",
        "programming_language",
        "attempt_number",
        "final_verdict",
        "source_code",
    ]

    feature_columns = [
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
        "programming_language",
    ]

    output_columns = list(dict.fromkeys(
    metadata_columns + feature_columns + ["is_unsuccessful"]
    ))

    return result.loc[:, output_columns].copy()


if __name__ == "__main__":
    dataset = build_codestream_dataset()

    print("CodeStream feature pipeline validation")
    print("--------------------------------------")
    print("Rows:", len(dataset))
    print("Unique users:", dataset["user_id"].nunique())
    print("Unique problems:", dataset["problem_id"].nunique())

    print("\nTarget distribution:")
    print(
        dataset["is_unsuccessful"]
        .map({0: "Accepted", 1: "Unsuccessful"})
        .value_counts()
    )

    print("\nProgramming languages:")
    print(dataset["programming_language"].value_counts(dropna=False))

    print("\nMissing source-code records:",
          int(dataset["source_code"].isna().sum()))

    print("\nRows with unobserved earlier attempt numbers:",
          int(
              (
                  dataset[
                      "unobserved_attempt_numbers_before_current"
                  ] > 0
              ).sum()
          ))

    print("\nNo files were written by this script.")
