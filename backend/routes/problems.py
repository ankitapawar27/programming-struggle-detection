
from flask import Blueprint, request, jsonify
from backend.database import get_db_connection

problems_bp = Blueprint("problems", __name__)


@problems_bp.route("/problems", methods=["POST"])
def add_problem():
    data = request.get_json(silent=True) or {}

    problem_title = data.get("problem_title")
    concept = data.get("concept")
    difficulty = data.get("difficulty")
    problem_description = data.get("problem_description")

    if not problem_title or not problem_title.strip():
        return jsonify({
            "error": "Problem title is required"
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        query = """
            INSERT INTO problem
            (problem_title, concept, difficulty, problem_description)
            VALUES (%s, %s, %s, %s)
        """

        cursor.execute(
            query,
            (
                problem_title.strip(),
                concept,
                difficulty,
                problem_description
            )
        )
        connection.commit()

        return jsonify({
            "message": "Problem added successfully",
            "problem_id": cursor.lastrowid,
            "problem_title": problem_title.strip(),
            "concept": concept,
            "difficulty": difficulty,
            "problem_description": problem_description
        }), 201

    except Exception:
        if connection:
            connection.rollback()

        problems_bp.logger.exception("Could not add problem")

        return jsonify({
            "error": "Could not add problem"
        }), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


@problems_bp.route("/problems", methods=["GET"])
def get_problems():
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                problem_id,
                problem_title,
                concept,
                difficulty,
                problem_description
            FROM problem
            ORDER BY problem_id DESC
        """)

        problems = cursor.fetchall()

        return jsonify(problems), 200

    except Exception:
        problems_bp.logger.exception("Could not retrieve problems")

        return jsonify({
            "error": "Could not retrieve problems"
        }), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()
