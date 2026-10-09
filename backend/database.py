
import os
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv

# Load .env from the main project folder
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def get_db_connection():
    """Connect to the project MySQL database."""
    password = os.getenv("DB_PASSWORD")

    if not password:
        raise RuntimeError(
            "DB_PASSWORD is missing. Check the project .env file."
        )

    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=password,
        database=os.getenv(
            "DB_NAME",
            "programming_struggle_detection"
        )
    )
