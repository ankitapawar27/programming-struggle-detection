
from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from backend.database import get_db_connection

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/test", methods=["GET"])
def auth_test():
    return jsonify({
        "status": "success",
        "message": "Authentication route is working"
    }), 200


@auth_bp.route("/signup", methods=["POST"])
def signup():
    data = request.get_json(silent=True) or {}

    name = data.get("student_name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not name or not email or not password:
        return jsonify({
            "error": "Name, email and password are required"
        }), 400

    if len(password) < 8:
        return jsonify({
            "error": "Password must be at least 8 characters"
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "SELECT student_id FROM student WHERE email = %s",
            (email,)
        )
        if cursor.fetchone():
            return jsonify({"error": "Email already registered"}), 409

        password_hash = generate_password_hash(password)

        cursor.execute(
            """
            INSERT INTO student (student_name, email, password_hash)
            VALUES (%s, %s, %s)
            """,
            (name, email, password_hash)
        )
        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Registration successful"
        }), 201

    except Exception:
        if connection:
            connection.rollback()
        auth_bp.logger.exception("Signup failed")
        return jsonify({"error": "Registration failed"}), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({
            "error": "Email and password are required"
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT student_id, student_name, email, password_hash
            FROM student
            WHERE email = %s
            """,
            (email,)
        )
        student = cursor.fetchone()

        if (
            not student
            or not student["password_hash"]
            or not check_password_hash(
                student["password_hash"], password
            )
        ):
            return jsonify({"error": "Invalid email or password"}), 401

        session.clear()
        session["student_id"] = student["student_id"]
        session["student_name"] = student["student_name"]
        session.permanent = False

        return jsonify({
            "status": "success",
            "message": "Login successful",
            "student": {
                "student_id": student["student_id"],
                "student_name": student["student_name"],
                "email": student["email"]
            }
        }), 200

    except Exception:
        auth_bp.logger.exception("Login failed")
        return jsonify({"error": "Login failed"}), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({
        "status": "success",
        "message": "Logged out successfully"
    }), 200


@auth_bp.route("/me", methods=["GET"])
def current_user():
    if "student_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    return jsonify({
        "student_id": session["student_id"],
        "student_name": session["student_name"]
    }), 200
