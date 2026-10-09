
from flask import Blueprint, jsonify

from backend.services.feature_extractor import extract_features
from ml.predict import predict_struggle

prediction_bp = Blueprint("prediction", __name__)


@prediction_bp.route("/predictions/<int:submission_id>", methods=["GET"])
def get_prediction(submission_id):
    try:
        # Extract features from the selected submission
        features = extract_features(submission_id)

        # Keep only the features required by the ML model
        model_features = {
            "attempt_number": features["attempt_number"],
            "error_count": features["error_count"],
            "execution_count": features["execution_count"],
            "time_spent_seconds": features["time_spent_seconds"],
            "total_events": features["total_events"],
            "execution_events": int(features["execution_events"]),
            "error_events": int(features["error_events"]),
            "submission_events": int(features["submission_events"])
        }

        # Generate the ML prediction
        result = predict_struggle(model_features)

        return jsonify({
            "submission_id": submission_id,
            "features": model_features,
            "prediction": result["struggle_level"],
            "class_probabilities": result["class_probabilities"],
            "model_type": result["model_type"]
        }), 200

    except ValueError as error:
        return jsonify({
            "error": str(error)
        }), 400

    except FileNotFoundError as error:
        prediction_bp.logger.exception("Prediction model unavailable")

        return jsonify({
            "error": "Prediction model is not available. Train the model first."
        }), 503

    except Exception:
        prediction_bp.logger.exception("Prediction failed")

        return jsonify({
            "error": "Could not generate prediction"
        }), 500
