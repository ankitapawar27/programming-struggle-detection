
from flask import Flask, jsonify
from backend.database import get_db_connection
from backend.routes.students import students_bp
from backend.routes.problems import problems_bp
from backend.routes.submissions import submissions_bp
app = Flask(__name__)

# Register Student API routes
app.register_blueprint(students_bp)
app.register_blueprint(problems_bp)
app.register_blueprint(submissions_bp)

@app.route("/")
def home():
    return jsonify({
        "project": "Programming Struggle Detection",
        "message": "Backend is running successfully!"
    })


@app.route("/health")
def health():
    return jsonify({
        "status": "healthy"
    })


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
