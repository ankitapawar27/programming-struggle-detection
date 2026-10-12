
from flask import Blueprint, request, jsonify
from backend.database import get_db_connection

students_bp = Blueprint("students", __name__)


@students_bp.route("/students", methods=["POST"])
def add_student():
    data = request.get_json(silent=True) or {}

    student_name = data.get("student_name")
    email = data.get("email")

    if not student_name:
        return jsonify({
            "error": "Student name is required"
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        query = """
            INSERT INTO student (student_name, email)
            VALUES (%s, %s)
        """

        cursor.execute(query, (student_name, email))
        connection.commit()

        return jsonify({
            "message": "Student added successfully",
            "student_id": cursor.lastrowid,
            "student_name": student_name,
            "email": email
        }), 201

    except Exception as error:
        if connection:
            connection.rollback()

        if getattr(error, "errno", None) == 1062:
            return jsonify({
                "error": "This email is already registered"
            }), 409

        students_bp.logger.exception("Could not add student")

        return jsonify({
            "error": "Could not add student"
        }), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


@students_bp.route("/students", methods=["GET"])
def get_students():
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT student_id, student_name, email, created_at
            FROM student
            ORDER BY student_id DESC
        """)

        students = cursor.fetchall()

        return jsonify(students), 200

    except Exception:
        students_bp.logger.exception("Could not retrieve students")

        return jsonify({
            "error": "Could not retrieve students"
        }), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()
