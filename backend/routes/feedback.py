
from flask import Blueprint, request, jsonify
from backend.database import get_db_connection

feedback_bp = Blueprint("feedback", __name__)


@feedback_bp.route("/feedback", methods=["POST"])
def add_feedback():
    data = request.get_json(silent=True) or {}

    prediction_id = data.get("prediction_id")
    feedback_text = data.get("feedback_text")

    if prediction_id is None:
        return jsonify({
            "error": "prediction_id is required"
        }), 400

    if not isinstance(feedback_text, str) or not feedback_text.strip():
        return jsonify({
            "error": "feedback_text is required"
        }), 400

    try:
        prediction_id = int(prediction_id)
    except (ValueError, TypeError):
        return jsonify({
            "error": "prediction_id must be an integer"
        }), 400

    if prediction_id < 1:
        return jsonify({
            "error": "prediction_id must be positive"
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO feedback (prediction_id, feedback_text)
            VALUES (%s, %s)
            """,
            (prediction_id, feedback_text.strip())
        )

        connection.commit()
        feedback_id = cursor.lastrowid

        return jsonify({
            "message": "Feedback added successfully",
            "feedback_id": feedback_id,
            "prediction_id": prediction_id,
            "feedback_text": feedback_text.strip()
        }), 201

    except Exception as error:
        if connection:
            connection.rollback()

        if getattr(error, "errno", None) == 1452:
            return jsonify({
                "error": "Prediction ID does not exist"
            }), 400

        feedback_bp.logger.exception("Could not save feedback")

        return jsonify({
            "error": "Could not save feedback"
        }), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


@feedback_bp.route("/predictions/<int:prediction_id>/feedback", methods=["GET"])
def get_feedback(prediction_id):
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT feedback_id, prediction_id, feedback_text, created_at
            FROM feedback
            WHERE prediction_id = %s
            ORDER BY feedback_id DESC
            """,
            (prediction_id,)
        )

        records = cursor.fetchall()

        for record in records:
            if record.get("created_at"):
                record["created_at"] = record["created_at"].isoformat(sep=" ")

        return jsonify(records), 200

    except Exception:
        feedback_bp.logger.exception("Could not retrieve feedback")

        return jsonify({
            "error": "Could not retrieve feedback"
        }), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()
