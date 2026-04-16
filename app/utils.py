import logging
import os
import random
import string
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db import redis_conn
from app.models.url import URLModel


BASE62_CHARS = string.ascii_letters + string.digits
BASE = len(BASE62_CHARS)


class AppLogger:
    """
    Centralized logger for the application. Logs to both file and console.
    """

    LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
    LOG_FILE = os.path.join(LOG_DIR, "app.log")

    @staticmethod
    def get_logger(name: str = "url_shortener"):
        if not os.path.exists(AppLogger.LOG_DIR):
            os.makedirs(AppLogger.LOG_DIR, exist_ok=True)
        logger = logging.getLogger(name)
        if not logger.handlers:
            file_handler = logging.FileHandler(AppLogger.LOG_FILE)
            stream_handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
            )
            file_handler.setFormatter(formatter)
            stream_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            logger.addHandler(stream_handler)
            logger.setLevel(logging.INFO)
        return logger


def get_record_by_field(
    db: Session, model: Any, field: str, value: Any
) -> Optional[Any]:
    """
    Generic utility to fetch a record from the database by a given field and value.
    Example: get_record_by_field(db, URLModel, 'long_url', long_url)
    """
    logger = AppLogger().get_logger()
    try:
        logger.info(
            f"Querying database for {model.__name__} where {field} = {value}"
        )
        return db.query(model).filter(getattr(model, field) == value).first()
    except Exception as e:
        logger.exception(
            f"Error querying database for {model.__name__} where {field} = {value}. Error: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


def get_expiry_date(expiry: Optional[int]) -> Optional[datetime]:
    """
    Utility to calculate the expiry datetime based on the provided expiry duration in seconds.
    If expiry is None, it returns None (indicating no expiration).
    """
    logger = AppLogger().get_logger()
    if expiry:
        try:
            expiry_dt = datetime.fromisoformat(expiry)
            if expiry_dt < datetime.now():
                logger.warning(
                    f"Provided expiry date {expiry} is in the past. Setting expiry to 30 days from now."
                )
                expiry_dt = datetime.now() + timedelta(days=30)
        except Exception:
            logger.warning(
                f"Invalid expiry format: {expiry}, using default 30 days."
            )
            expiry_dt = datetime.now() + timedelta(days=30)
    else:
        expiry_dt = datetime.now() + timedelta(days=30)
    return expiry_dt


def generate_code(length: int = 7) -> str:
    """
    Generate a random Base62 short code.
    """
    return "".join(random.choices(BASE62_CHARS, k=length))


def generate_unique_code(db: Session, max_retries: int = 5) -> str:
    """
    Generate a unique short_code by checking DB.
    """
    for _ in range(max_retries):
        code = generate_code()
        # Check if the generated code already exists in the database
        exists = (
            db.query(URLModel.id).filter(URLModel.short_code == code).first()
        )
        # If it doesn't exist, return the code
        if not exists:
            return code

    raise Exception("Failed to generate unique short code after retries")
