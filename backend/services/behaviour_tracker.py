
import json

from backend.database import get_db_connection


def log_behaviour(submission_id, event_type, event_details=None):
    """
    Store a coding behaviour event in the MySQL database.
    """

    if not event_type or not event_type.strip():
        raise ValueError("event_type is required")

    try:
        submission_id = int(submission_id)
    except (TypeError, ValueError):
        raise ValueError("submission_id must be an integer") from None

    if submission_id < 1:
        raise ValueError("submission_id must be positive")

    if event_details is not None and not isinstance(event_details, str):
        event_details = json.dumps(event_details)

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        query = """
            INSERT INTO behaviour_log
                (submission_id, event_type, event_details)
            VALUES (%s, %s, %s)
        """

        cursor.execute(
            query,
            (submission_id, event_type.strip(), event_details)
        )
        connection.commit()

        return {
            "message": "Behaviour event logged successfully",
            "log_id": cursor.lastrowid,
            "submission_id": submission_id,
            "event_type": event_type.strip()
        }

    except Exception:
        if connection:
            connection.rollback()
        raise

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()
