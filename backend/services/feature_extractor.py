
from backend.database import get_db_connection


def extract_features(submission_id):
    """
    Extract numerical features for one coding submission.

    Submission metrics come from submission.
    Execution metrics come from execution_log.
    Other behaviour events come from behaviour_log.

    The returned feature names remain compatible with the
    existing ML feature_engineering.py file.
    """

    try:
        submission_id = int(submission_id)
    except (TypeError, ValueError):
        raise ValueError("submission_id must be an integer") from None

    if submission_id < 1:
        raise ValueError("submission_id must be positive")

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # 1. Get the saved submission metrics.
        cursor.execute(
            """
            SELECT
                submission_id,
                student_id,
                problem_id,
                attempt_number,
                error_count,
                execution_count,
                time_spent_seconds
            FROM submission
            WHERE submission_id = %s
            """,
            (submission_id,)
        )

        submission = cursor.fetchone()

        if submission is None:
            raise ValueError(
                f"Submission {submission_id} was not found"
            )

        # 2. Count behaviour events.
        # Execution events are counted separately from execution_log
        # to avoid counting the same run twice.
        cursor.execute(
            """
            SELECT
                COUNT(
                    CASE
                        WHEN event_type NOT IN (
                            'code_execution',
                            'execution_success',
                            'execution_error',
                            'execution_timeout'
                        )
                        THEN 1
                    END
                ) AS other_events,

                COUNT(
                    CASE
                        WHEN event_type = 'error'
                        THEN 1
                    END
                ) AS behaviour_error_events,

                COUNT(
                    CASE
                        WHEN event_type = 'submission_created'
                        THEN 1
                    END
                ) AS submission_events

            FROM behaviour_log
            WHERE submission_id = %s
            """,
            (submission_id,)
        )

        behaviour = cursor.fetchone() or {}

        # 3. Count executions saved for this exact submission.
        cursor.execute(
            """
            SELECT
                COUNT(*) AS execution_events,

                COUNT(
                    CASE
                        WHEN event_type IN (
                            'execution_error',
                            'execution_timeout'
                        )
                        THEN 1
                    END
                ) AS execution_error_events

            FROM execution_log
            WHERE submission_id = %s
            """,
            (submission_id,)
        )

        execution = cursor.fetchone() or {}

        other_events = int(behaviour.get("other_events") or 0)
        execution_events = int(
            execution.get("execution_events") or 0
        )

        behaviour_error_events = int(
            behaviour.get("behaviour_error_events") or 0
        )

        execution_error_events = int(
            execution.get("execution_error_events") or 0
        )

        submission_events = int(
            behaviour.get("submission_events") or 0
        )

        # 4. Return the existing eight ML feature columns.
        features = {
            "submission_id": submission["submission_id"],
            "student_id": submission["student_id"],
            "problem_id": submission["problem_id"],

            "attempt_number": submission["attempt_number"] or 0,
            "error_count": submission["error_count"] or 0,
            "execution_count": submission["execution_count"] or 0,
            "time_spent_seconds": (
                submission["time_spent_seconds"] or 0
            ),

            "total_events": other_events + execution_events,
            "execution_events": execution_events,
            "error_events": (
                behaviour_error_events + execution_error_events
            ),
            "submission_events": submission_events
        }

        return features

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()
