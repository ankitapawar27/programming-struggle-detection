
from flask import Blueprint, request, jsonify
from backend.database import get_db_connection

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

    if student_id is None or problem_id is None:
        return jsonify({
            "error": "student_id and problem_id are required"
        }), 400

    if not code_text or not code_text.strip():
        return jsonify({
            "error": "code_text is required"
        }), 400

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

    if (
        student_id < 1
        or problem_id < 1
        or attempt_number < 1
        or error_count < 0
        or execution_count < 0
        or time_spent_seconds < 0
    ):
        return jsonify({
            "error": "IDs and attempt number must be positive; metrics cannot be negative"
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        query = """
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
        """

        cursor.execute(
            query,
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

        return jsonify({
            "message": "Submission added successfully",
            "submission_id": submission_id,
            "student_id": student_id,
            "problem_id": problem_id
        }), 201

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


@submissions_bp.route("/submissions", methods=["GET"])
def get_submissions():
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
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
        """)

        submissions = cursor.fetchall()

        for submission in submissions:
            if submission.get("submitted_at"):
                submission["submitted_at"] = (
                    submission["submitted_at"].isoformat(sep=" ")
                )

        return jsonify(submissions), 200

    except Exception:
        submissions_bp.logger.exception("Could not retrieve submissions")

        return jsonify({
            "error": "Could not retrieve submissions"
        }), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()
