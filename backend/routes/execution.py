
import os
import subprocess
import sys
import tempfile
import time

from flask import Blueprint, jsonify, request, current_app
from pathlib import Path
from backend.database import get_db_connection

execution_bp = Blueprint("execution", __name__)

MAX_CODE_LENGTH = 20_000
EXECUTION_TIMEOUT_SECONDS = 3
MAX_OUTPUT_LENGTH = 10_000

JAVA_HOME = Path(
    r"C:\Program Files\Eclipse Adoptium\jdk-21.0.12.101-hotspot"
)

JAVAC_PATH = str(JAVA_HOME / "bin" / "javac.exe")
JAVA_PATH = str(JAVA_HOME / "bin" / "java.exe")

def save_execution_log(
    submission_id,
    event_type,
    execution_time_ms=None,
    return_code=None,
    timed_out=False,
    stdout="",
    stderr=""
):
    """Save an execution event to MySQL."""
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        if submission_id is not None:
            cursor.execute(
                """
                SELECT submission_id
                FROM submission
                WHERE submission_id = %s
                """,
                (submission_id,)
            )

            if cursor.fetchone() is None:
                raise ValueError(
                    "The supplied submission ID does not exist."
                )

        cursor.execute(
            """
            INSERT INTO execution_log (
                submission_id,
                event_type,
                execution_time_ms,
                return_code,
                timed_out,
                stdout,
                stderr
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                submission_id,
                event_type,
                execution_time_ms,
                return_code,
                timed_out,
                stdout[:MAX_OUTPUT_LENGTH],
                stderr[:MAX_OUTPUT_LENGTH]
            )
        )

        execution_id = cursor.lastrowid
        connection.commit()
        return execution_id

    except Exception:
        if connection:
            connection.rollback()
        raise

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


def persist_execution_safely(**details):
    """Do not hide the execution result if logging fails."""
    try:
        return save_execution_log(**details)
    except Exception:
        execution_bp.logger.exception(
            "Execution completed, but its log could not be saved."
        )
        return None


@execution_bp.route("/execute", methods=["POST"])
def execute_python():
    data = request.get_json(silent=True) or {}
    code = data.get("code")
    raw_submission_id = data.get("submission_id")

    if not isinstance(code, str) or not code.strip():
        return jsonify({
            "success": False,
            "error": "Please enter Python code."
        }), 400

    if len(code) > MAX_CODE_LENGTH:
        return jsonify({
            "success": False,
            "error": "Code is too long. Maximum size is 20,000 characters."
        }), 413

    submission_id = None

    if raw_submission_id is not None:
        try:
            submission_id = int(raw_submission_id)
            if submission_id < 1:
                raise ValueError
        except (TypeError, ValueError):
            return jsonify({
                "success": False,
                "error": "submission_id must be a positive integer."
            }), 400

    started = time.perf_counter()

    try:
        with tempfile.TemporaryDirectory(
            prefix="psd_run_"
        ) as temp_dir:
            script_path = os.path.join(
                temp_dir, "solution.py"
            )

            with open(
                script_path, "w", encoding="utf-8"
            ) as script:
                script.write(code)

            try:
                result = subprocess.run(
                    [sys.executable, "-I", script_path],
                    cwd=temp_dir,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=EXECUTION_TIMEOUT_SECONDS,
                    check=False,
                    shell=False
                )

                elapsed_ms = round(
                    (time.perf_counter() - started) * 1000,
                    2
                )

                stdout = result.stdout[:MAX_OUTPUT_LENGTH]
                stderr = result.stderr[:MAX_OUTPUT_LENGTH]
                success = result.returncode == 0

                event_type = (
                    "execution_success"
                    if success
                    else "execution_error"
                )

                execution_id = persist_execution_safely(
                    submission_id=submission_id,
                    event_type=event_type,
                    execution_time_ms=elapsed_ms,
                    return_code=result.returncode,
                    timed_out=False,
                    stdout=stdout,
                    stderr=stderr
                )

                return jsonify({
                    "success": success,
                    "stdout": stdout,
                    "stderr": stderr,
                    "return_code": result.returncode,
                    "execution_time_ms": elapsed_ms,
                    "timed_out": False,
                    "output_truncated": (
                        len(result.stdout) > MAX_OUTPUT_LENGTH
                        or len(result.stderr) > MAX_OUTPUT_LENGTH
                    ),
                    "execution_id": execution_id,
                    "execution_logged": execution_id is not None
                }), 200

            except subprocess.TimeoutExpired as error:
                elapsed_ms = round(
                    (time.perf_counter() - started) * 1000,
                    2
                )

                partial_stdout = error.stdout or ""
                partial_stderr = error.stderr or ""

                if isinstance(partial_stdout, bytes):
                    partial_stdout = partial_stdout.decode(
                        "utf-8", errors="replace"
                    )

                if isinstance(partial_stderr, bytes):
                    partial_stderr = partial_stderr.decode(
                        "utf-8", errors="replace"
                    )

                partial_stdout = partial_stdout[:MAX_OUTPUT_LENGTH]
                partial_stderr = partial_stderr[:MAX_OUTPUT_LENGTH]

                execution_id = persist_execution_safely(
                    submission_id=submission_id,
                    event_type="execution_timeout",
                    execution_time_ms=elapsed_ms,
                    return_code=None,
                    timed_out=True,
                    stdout=partial_stdout,
                    stderr=partial_stderr
                )

                return jsonify({
                    "success": False,
                    "stdout": partial_stdout,
                    "stderr": partial_stderr,
                    "error": (
                        "Execution timed out after "
                        f"{EXECUTION_TIMEOUT_SECONDS} seconds."
                    ),
                    "execution_time_ms": elapsed_ms,
                    "timed_out": True,
                    "execution_id": execution_id,
                    "execution_logged": execution_id is not None
                }), 200

    except OSError:
        execution_bp.logger.exception(
            "Python execution process could not be started."
        )

        return jsonify({
            "success": False,
            "error": "The local Python process could not be started."
        }), 500


@execution_bp.route("/execute/java", methods=["POST"])
def execute_java():
    data = request.get_json(silent=True) or {}
    code = data.get("code")
    raw_submission_id = data.get("submission_id")

    if not isinstance(code, str) or not code.strip():
        return jsonify({
            "success": False,
            "error": "Please enter Java code."
        }), 400

    if len(code) > MAX_CODE_LENGTH:
        return jsonify({
            "success": False,
            "error": "Code is too long. Maximum size is 20,000 characters."
        }), 413

    submission_id = None
    if raw_submission_id is not None:
        try:
            submission_id = int(raw_submission_id)
            if submission_id < 1:
                raise ValueError
        except (TypeError, ValueError):
            return jsonify({
                "success": False,
                "error": "submission_id must be a positive integer."
            }), 400

    started = time.perf_counter()

    try:
        with tempfile.TemporaryDirectory(prefix="psd_java_") as temp_dir:
            source_path = os.path.join(temp_dir, "Main.java")

            with open(source_path, "w", encoding="utf-8") as source:
                source.write(code)

            compile_result = subprocess.run(
                [JAVAC_PATH, "-encoding", "UTF-8", source_path],
                cwd=temp_dir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=EXECUTION_TIMEOUT_SECONDS,
                check=False,
                shell=False
            )

            if compile_result.returncode != 0:
                elapsed_ms = round(
                    (time.perf_counter() - started) * 1000, 2
                )
                stderr = compile_result.stderr[:MAX_OUTPUT_LENGTH]

                execution_id = persist_execution_safely(
                    submission_id=submission_id,
                    event_type="execution_error",
                    execution_time_ms=elapsed_ms,
                    return_code=compile_result.returncode,
                    timed_out=False,
                    stdout=compile_result.stdout,
                    stderr=stderr
                )

                return jsonify({
                    "success": False,
                    "stdout": compile_result.stdout[:MAX_OUTPUT_LENGTH],
                    "stderr": stderr,
                    "error": "Java compilation failed.",
                    "return_code": compile_result.returncode,
                    "execution_time_ms": elapsed_ms,
                    "timed_out": False,
                    "execution_id": execution_id,
                    "execution_logged": execution_id is not None
                }), 200

            result = subprocess.run(
                [JAVA_PATH, "-cp", temp_dir, "Main"],
                cwd=temp_dir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=EXECUTION_TIMEOUT_SECONDS,
                check=False,
                shell=False
            )

            elapsed_ms = round(
                (time.perf_counter() - started) * 1000, 2
            )
            stdout = result.stdout[:MAX_OUTPUT_LENGTH]
            stderr = result.stderr[:MAX_OUTPUT_LENGTH]
            success = result.returncode == 0

            execution_id = persist_execution_safely(
                submission_id=submission_id,
                event_type=(
                    "execution_success" if success else "execution_error"
                ),
                execution_time_ms=elapsed_ms,
                return_code=result.returncode,
                timed_out=False,
                stdout=stdout,
                stderr=stderr
            )

            return jsonify({
                "success": success,
                "stdout": stdout,
                "stderr": stderr,
                "return_code": result.returncode,
                "execution_time_ms": elapsed_ms,
                "timed_out": False,
                "execution_id": execution_id,
                "execution_logged": execution_id is not None
            }), 200

    except subprocess.TimeoutExpired:
        elapsed_ms = round(
            (time.perf_counter() - started) * 1000, 2
        )

        execution_id = persist_execution_safely(
            submission_id=submission_id,
            event_type="execution_timeout",
            execution_time_ms=elapsed_ms,
            return_code=None,
            timed_out=True,
            stdout="",
            stderr="Java execution or compilation timed out."
        )

        return jsonify({
            "success": False,
            "stdout": "",
            "stderr": "Java execution or compilation timed out.",
            "error": (
                f"Java execution timed out after "
                f"{EXECUTION_TIMEOUT_SECONDS} seconds."
            ),
            "execution_time_ms": elapsed_ms,
            "timed_out": True,
            "execution_id": execution_id,
            "execution_logged": execution_id is not None
        }), 200

    except OSError:
        current_app.logger.exception("Java process could not be started.")
        return jsonify({
            "success": False,
            "error": "Java compiler or runtime could not be started. Check JAVA_HOME and PATH."
        }), 500


@execution_bp.route("/execute/javascript", methods=["POST"])
def execute_javascript():
    data = request.get_json(silent=True) or {}
    code = data.get("code")
    raw_submission_id = data.get("submission_id")

    if not isinstance(code, str) or not code.strip():
        return jsonify({
            "success": False,
            "error": "Please enter JavaScript code."
        }), 400

    if len(code) > MAX_CODE_LENGTH:
        return jsonify({
            "success": False,
            "error": "Code is too long. Maximum size is 20,000 characters."
        }), 413

    submission_id = None
    if raw_submission_id is not None:
        try:
            submission_id = int(raw_submission_id)
            if submission_id < 1:
                raise ValueError
        except (TypeError, ValueError):
            return jsonify({
                "success": False,
                "error": "submission_id must be a positive integer."
            }), 400

    started = time.perf_counter()

    try:
        with tempfile.TemporaryDirectory(prefix="psd_js_") as temp_dir:
            script_path = os.path.join(temp_dir, "solution.js")

            with open(script_path, "w", encoding="utf-8") as script:
                script.write(code)

            result = subprocess.run(
                ["node", script_path],
                cwd=temp_dir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=EXECUTION_TIMEOUT_SECONDS,
                check=False,
                shell=False
            )

            elapsed_ms = round(
                (time.perf_counter() - started) * 1000, 2
            )
            stdout = result.stdout[:MAX_OUTPUT_LENGTH]
            stderr = result.stderr[:MAX_OUTPUT_LENGTH]
            success = result.returncode == 0

            execution_id = persist_execution_safely(
                submission_id=submission_id,
                event_type=(
                    "execution_success" if success else "execution_error"
                ),
                execution_time_ms=elapsed_ms,
                return_code=result.returncode,
                timed_out=False,
                stdout=stdout,
                stderr=stderr
            )

            return jsonify({
                "success": success,
                "stdout": stdout,
                "stderr": stderr,
                "return_code": result.returncode,
                "execution_time_ms": elapsed_ms,
                "timed_out": False,
                "execution_id": execution_id,
                "execution_logged": execution_id is not None
            }), 200

    except subprocess.TimeoutExpired:
        elapsed_ms = round(
            (time.perf_counter() - started) * 1000, 2
        )

        execution_id = persist_execution_safely(
            submission_id=submission_id,
            event_type="execution_timeout",
            execution_time_ms=elapsed_ms,
            return_code=None,
            timed_out=True,
            stdout="",
            stderr="JavaScript execution timed out."
        )

        return jsonify({
            "success": False,
            "stdout": "",
            "stderr": "JavaScript execution timed out.",
            "error": (
                f"JavaScript execution timed out after "
                f"{EXECUTION_TIMEOUT_SECONDS} seconds."
            ),
            "execution_time_ms": elapsed_ms,
            "timed_out": True,
            "execution_id": execution_id,
            "execution_logged": execution_id is not None
        }), 200

    except OSError:
        current_app.logger.exception(
            "JavaScript process could not be started."
        )
        return jsonify({
            "success": False,
            "error": "Node.js could not be started. Check its installation and PATH."
        }), 500


@execution_bp.route("/execute/c", methods=["POST"])
def execute_c():
    data = request.get_json(silent=True) or {}
    code = data.get("code", "")

    if not isinstance(code, str) or not code.strip():
        return jsonify({"error": "Please enter a C program."}), 400

    if len(code) > MAX_CODE_LENGTH:
        return jsonify({"error": "Code is too long."}), 400

    gcc_path = r"C:\msys64\ucrt64\bin\gcc.exe"
    gcc_env = os.environ.copy()
    gcc_env["PATH"] = r"C:\msys64\ucrt64\bin" + os.pathsep + gcc_env.get("PATH", "")
    start_time = time.time()

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = os.path.join(temp_dir, "main.c")
            executable_path = os.path.join(temp_dir, "main.exe")

            with open(source_path, "w", encoding="utf-8") as file:
                file.write(code)

            # Compile the C program
            try:
                compile_result = subprocess.run(
                    [gcc_path, source_path, "-o", executable_path],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=temp_dir,
                    env=gcc_env
                )

            except subprocess.TimeoutExpired:
                return jsonify({
                    "output": "",
                    "error": "C compilation timed out."
                }), 200

            if compile_result.returncode != 0:
                return jsonify({
                    "output": "",
                    "error": compile_result.stderr[:MAX_OUTPUT_LENGTH],
                    "execution_time": round(time.time() - start_time, 3)
                }), 200

            # Execute the compiled program
            try:
                result = subprocess.run(
                    [executable_path],
                    capture_output=True,
                    text=True,
                    timeout=EXECUTION_TIMEOUT_SECONDS,
                    cwd=temp_dir,
                    env=gcc_env
                )

            except subprocess.TimeoutExpired:
                return jsonify({
                    "output": "",
                    "error": "Execution timed out."
                }), 200
            
            persist_execution_safely(
    submission_id=data.get("submission_id"),
    event_type=(
        "execution success"
        if result.returncode == 0
        else "execution error"
    ),
    execution_time_ms=round((time.time() - start_time) * 1000, 2),
    return_code=result.returncode,
    timed_out=False,
    stdout=result.stdout,
    stderr=result.stderr
)
            return jsonify({
    "success": result.returncode == 0,
    "output": result.stdout[:MAX_OUTPUT_LENGTH],
    "error": result.stderr[:MAX_OUTPUT_LENGTH],
    "stderr": result.stderr[:MAX_OUTPUT_LENGTH],
    "returncode": result.returncode,
    "execution_time": round(time.time() - start_time, 3),
    "execution_time_ms": round((time.time() - start_time) * 1000, 2)
}), 200

    except FileNotFoundError:
        current_app.logger.exception("GCC executable was not found.")
        return jsonify({
            "error": "GCC was not found. Check the compiler path."
        }), 500

    except Exception:
        current_app.logger.exception("C execution failed.")
        return jsonify({
            "error": "An unexpected error occurred during C execution."
        }), 500

@execution_bp.route("/executions", methods=["GET"])
def get_execution_history():
    """Return the latest saved execution records."""
    connection = None
    cursor = None

    limit = request.args.get("limit", default=50, type=int)

    if limit is None or not 1 <= limit <= 200:
        return jsonify({
            "error": "limit must be between 1 and 200"
        }), 400

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                execution_id,
                submission_id,
                event_type,
                execution_time_ms,
                return_code,
                timed_out,
                stdout,
                stderr,
                created_at
            FROM execution_log
            ORDER BY execution_id DESC
            LIMIT %s
            """,
            (limit,)
        )

        records = cursor.fetchall()

        for record in records:
            if record.get("created_at"):
                record["created_at"] = (
                    record["created_at"].isoformat(sep=" ")
                )

            if record.get("execution_time_ms") is not None:
                record["execution_time_ms"] = float(
                    record["execution_time_ms"]
                )

            if record.get("timed_out") is not None:
                record["timed_out"] = bool(
                    record["timed_out"]
                )

        return jsonify({
            "count": len(records),
            "executions": records
        }), 200

    except Exception:
        current_app.logger.exception(
            "Could not retrieve execution history."
        )

        return jsonify({
            "error": "Could not retrieve execution history."
        }), 500

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()
