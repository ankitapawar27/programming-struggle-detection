
from flask import Flask, jsonify
from database import get_db_connection

app = Flask(__name__)


@app.route("/")
def home():
    return jsonify({
        "project": "Programming Struggle Detection",
        "message": "Backend is running successfully!"
    })


@app.route("/health")
def health():
    return jsonify({"status": "healthy"})


@app.route("/db-health")
def db_health():
    try:
        connection = get_db_connection()
        connection.close()

        return jsonify({
            "status": "success",
            "message": "MySQL database connected successfully!"
        })

    except Exception:
        app.logger.exception("Database connection failed")

        return jsonify({
            "status": "error",
            "message": "Database connection failed"
        }), 500


if __name__ == "__main__":
    app.run(debug=True)
