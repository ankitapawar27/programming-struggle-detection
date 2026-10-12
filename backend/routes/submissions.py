
from flask import Blueprint, request, jsonify

from backend.database import get_db_connection
from backend.services.behaviour_tracker import log_behaviour

submissions_bp = Blueprint("submissions", __name__)


@submissions_bp.route("/submissions", methods=["POST"])
def add_submission():
    data = request.get_json(silent=True) or {}

    student_id = data.get("student_id")
    problem_id = data.get("problem_id")
    code_text = data.get("code_text")
    attempt_number = data.get("attempt_number", 1)
    error_count = data.get("error_count", 0)
    execution_count = data.get("execution_count", 0)
    time_spent_seconds = data.get("time_spent_seconds", 0)

    # Validate required fields.
    if student_id is None or problem_id is None:
        return jsonify({
            "error": "student_id and problem_id are required"
        }), 400

    if not isinstance(code_text, str) or not code_text.strip():
        return jsonify({
            "error": "code_text is required"
        }), 400

    # Validate integer fields.
    try:
        student_id = int(student_id)
        problem_id = int(problem_id)
        attempt_number = int(attempt_number)
        error_count = int(error_count)
        execution_count = int(execution_count)
        time_spent_seconds = int(time_spent_seconds)
    except (ValueError, TypeError):
        return jsonify({
            "error": "IDs and behaviour metrics must be integers"
        }), 400

    # Validate ranges.
    if (
        student_id < 1
        or problem_id < 1
        or attempt_number < 1
        or error_count < 0
        or execution_count < 0
        or time_spent_seconds < 0
    ):
        return jsonify({
            "error": (
                "IDs and attempt number must be positive; "
                "metrics cannot be negative"
            )
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO submission (
                student_id,
                problem_id,
                code_text,
                attempt_number,
                error_count,
                execution_count,
                time_spent_seconds
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                student_id,
                problem_id,
                code_text,
                attempt_number,
                error_count,
                execution_count,
                time_spent_seconds
            )
        )

        connection.commit()
        submission_id = cursor.lastrowid

    except Exception as error:
        if connection:
            connection.rollback()

        if getattr(error, "errno", None) == 1452:
            return jsonify({
                "error": "Student or problem ID does not exist"
            }), 400

        submissions_bp.logger.exception("Could not add submission")

        return jsonify({
            "error": "Could not add submission"
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()

    # Record submission creation after the submission is saved.
    try:
        log_behaviour(
            submission_id,
            "submission_created",
            {
                "attempt_number": attempt_number,
                "error_count": error_count,
                "execution_count": execution_count,
                "time_spent_seconds": time_spent_seconds
            }
        )
    except Exception:
        submissions_bp.logger.exception(
            "Submission saved, but behaviour logging failed"
        )

    return jsonify({
        "message": "Submission added successfully",
        "submission_id": submission_id,
        "student_id": student_id,
        "problem_id": problem_id
    }), 201


@submissions_bp.route(
    "/submissions/<int:submission_id>/behaviour",
    methods=["POST"]
)
def record_submission_behaviour(submission_id):
    data = request.get_json(silent=True) or {}
    event_type = data.get("event_type")

    if event_type != "error":
        return jsonify({
            "error": "event_type must be 'error'"
        }), 400

    try:
        log_behaviour(
            submission_id,
            "error",
            {"source": "manual_error_button"}
        )

        return jsonify({
            "message": "Behaviour event recorded",
            "submission_id": submission_id,
            "event_type": "error"
        }), 201

    except Exception:
        submissions_bp.logger.exception(
            "Could not record submission behaviour"
        )

        return jsonify({
            "error": "Could not record behaviour event"
        }), 500


@submissions_bp.route("/submissions", methods=["GET"])
def get_submissions():
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                submission_id,
                student_id,
                problem_id,
                code_text,
                attempt_number,
                error_count,
                execution_count,
                time_spent_seconds,
                submitted_at
            FROM submission
            ORDER BY submission_id DESC
            """
        )

        submissions = cursor.fetchall()

        for submission in submissions:
            if submission.get("submitted_at"):
                submission["submitted_at"] = (
                    submission["submitted_at"].isoformat(sep=" ")
                )

        return jsonify(submissions), 200

    except Exception:
        submissions_bp.logger.exception(
            "Could not retrieve submissions"
        )

        return jsonify({
            "error": "Could not retrieve submissions"
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()
