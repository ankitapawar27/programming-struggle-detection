
from flask import Blueprint, jsonify

from backend.database import get_db_connection
from backend.services.feature_extractor import extract_features
from ml.predict import predict_struggle
import joblib
import pandas as pd
from pathlib import Path
from flask import current_app
from ml.codestream_features import build_codestream_dataset

prediction_bp = Blueprint("prediction", __name__)


# Generate and save a prediction
@prediction_bp.route(
    "/predictions/<int:submission_id>",
    methods=["GET"]
)
def get_prediction(submission_id):
    try:
        # Extract features from the saved submission
        features = extract_features(submission_id)

        model_features = {
            "attempt_number": features["attempt_number"],
            "error_count": features["error_count"],
            "execution_count": features["execution_count"],
            "time_spent_seconds": features["time_spent_seconds"],
            "total_events": int(features["total_events"]),
            "execution_events": int(features["execution_events"]),
            "error_events": int(features["error_events"]),
            "submission_events": int(features["submission_events"])
        }

        # Generate the ML prediction
        result = predict_struggle(model_features)
        struggle_level = result["struggle_level"]
        

        # Save prediction in MySQL
        connection = None
        cursor = None

        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            prediction_score = float(result["no_struggle_percentage"])

            cursor.execute(
                """
                INSERT INTO prediction (
                    submission_id,
                    struggle_level,
                    prediction_score,
                    predicted_concept
                )
                VALUES (%s, %s, %s, %s)
                """,
                (
                    submission_id,
                    struggle_level,
                    prediction_score,
                    None
                )
            )

            connection.commit()
            prediction_id = cursor.lastrowid

        except Exception:
            if connection:
                connection.rollback()
            raise

        finally:
            if cursor:
                cursor.close()

            if connection and connection.is_connected():
                connection.close()
           
        return jsonify({
            "submission_id": submission_id,
            "struggle_level": result["struggle_level"],
            "indicator_score": result["indicator_score"],
            "no_struggle_percentage": result["no_struggle_percentage"],
            "reasons": result["reasons"],
            "model_type": result["model_type"],
            "message": result["message"]
        }), 200

    except ValueError as error:
        return jsonify({
            "error": str(error)
        }), 400

    except FileNotFoundError:
        current_app.logger.exception(
            "Prediction model unavailable"
        )

        return jsonify({
            "error": "Prediction model is not available. Train the model first."
        }), 503

    except Exception:
        current_app.logger.exception(
            "Prediction generation or database save failed"
        )

        return jsonify({
            "error": "Could not generate and save prediction"
        }), 500


# Retrieve prediction history for a submission
@prediction_bp.route(
    "/submissions/<int:submission_id>/predictions",
    methods=["GET"]
)
def get_prediction_history(submission_id):
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        # Check whether the submission exists
        cursor.execute(
            """
            SELECT submission_id
            FROM submission
            WHERE submission_id = %s
            """,
            (submission_id,)
        )

        if cursor.fetchone() is None:
            return jsonify({
                "error": f"Submission {submission_id} was not found"
            }), 404

        # Retrieve all saved predictions for this submission
        cursor.execute(
            """
            SELECT
                prediction_id,
                submission_id,
                struggle_level,
                prediction_score,
                predicted_concept,
                predicted_at
            FROM prediction
            WHERE submission_id = %s
            ORDER BY prediction_id DESC
            """,
            (submission_id,)
        )

        records = cursor.fetchall()

        # Convert MySQL values into JSON-compatible values
        for record in records:
            if record.get("prediction_score") is not None:
                record["prediction_score"] = float(
                    record["prediction_score"]
                )

            if record.get("predicted_at"):
                record["predicted_at"] = (
                    record["predicted_at"].isoformat(sep=" ")
                )

        return jsonify({
            "submission_id": submission_id,
            "count": len(records),
            "history": records
        }), 200

    except Exception:
        current_app.logger.exception(
            "Could not retrieve prediction history"
        )

        return jsonify({
            "error": "Could not retrieve prediction history"
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()
# List real CodeStream submissions for the dataset explorer
@prediction_bp.route(
    "/codestream/submissions",
    methods=["GET"]
)
def list_codestream_submissions():
    try:
        dataset = build_codestream_dataset()

        submissions = dataset[
            [
                "submission_id",
                "problem_id",
                "attempt_number",
                "programming_language",
                "final_verdict",
            ]
        ].copy()

        submissions = submissions.sort_values(
            "submission_id",
            ascending=False
        ).head(100)

        return jsonify({
            "count": len(submissions),
            "submissions": submissions.fillna("").to_dict(
                orient="records"
            )
        }), 200

    except FileNotFoundError:
        return jsonify({
            "error": "CodeStream dataset file was not found."
        }), 503

    except Exception:
        current_app.logger.exception(
            "Could not list CodeStream submissions"
        )
        return jsonify({
            "error": "Could not load CodeStream submissions."
        }), 500

# Experimental CodeStream verdict prediction
@prediction_bp.route(
    "/codestream/predictions/<string:submission_id>",
    methods=["GET"]
)
def get_codestream_prediction(submission_id):
    try:
        model_path = (
            Path(__file__).resolve().parents[2]
            / "ml"
            / "models"
            / "codestream_verdict_model.joblib"
        )

        if not model_path.exists():
            return jsonify({
                "error": "CodeStream model not found. Train it first."
            }), 503

        artifact = joblib.load(model_path)
        dataset = build_codestream_dataset()

        matches = dataset[
            dataset["submission_id"].astype(str) == submission_id
        ]

        if matches.empty:
            return jsonify({
                "error": "CodeStream submission not found"
            }), 404

        row = matches.iloc[[0]]
        feature_names = artifact["features"]
        model = artifact["model"]

        X = row[feature_names]
        prediction = int(model.predict(X)[0])
        probabilities = model.predict_proba(X)[0]
        classes = model.classes_

        verdict = artifact["target_mapping"][prediction]

        return jsonify({
            "submission_id": submission_id,
            "predicted_verdict": verdict,
            "class_probabilities": {
                artifact["target_mapping"][int(cls)]:
                    round(float(prob), 4)
                for cls, prob in zip(classes, probabilities)
            },
            "model_type": artifact["model_type"],
            "experimental": True,
            "message": (
                "Predicts submission verdict, not student struggle level."
            )
        }), 200

    except FileNotFoundError:
        return jsonify({
            "error": "CodeStream dataset or model file not found"
        }), 503

    except Exception:
        current_app.logger.exception(
            "CodeStream prediction failed"
        )
        return jsonify({
            "error": "Could not generate CodeStream prediction"
        }), 500
