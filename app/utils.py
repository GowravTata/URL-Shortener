import logging
import os
import hashlib
import base64

from app.db import redis_conn
from sqlalchemy.orm import Session
from typing import Any, Optional
from fastapi import HTTPException, status
from app.config import URL_EXISTS


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


def shorten_text(text):
    # Create hash
    hash_object = hashlib.sha256(text.encode())
    hash_bytes = hash_object.digest()

    # Convert to Base64 and trim
    short_code = base64.urlsafe_b64encode(hash_bytes).decode()[:6]

    return short_code


class RedisCache:
    """
    Simple Redis cache wrapper for get/set operations.
    """

    def __init__(self):
        self.redis_conn = redis_conn

    def set(self, key, value, ex=6000) -> None:
        # Set a value in Redis with an expiration time
        logger = AppLogger().get_logger()
        try:
            logger.info(
                f"Setting Redis cache for key: {key} with value: {value} and expiration: {ex} seconds"
            )
            self.redis_conn.set(key, value, ex=ex)
        except Exception as e:
            logger.exception(
                f"Error setting Redis cache for key: {key}. Error: {str(e)}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal Server Error",
            )

    def get(self, key) -> Optional[str]:
        # Get a value from Redis by key
        logger = AppLogger().get_logger()
        try:
            logger.info(f"Getting Redis cache for key: {key}")
            return self.redis_conn.get(key)
        except Exception as e:
            logger.exception(
                f"Error getting Redis cache for key: {key}. Error: {str(e)}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal Server Error",
            )

    def delete(self, key) -> None:
        # Delete a key from Redis
        logger = AppLogger().get_logger()
        try:
            logger.info(f"Deleting Redis cache for key: {key}")
            self.redis_conn.delete(key)
        except Exception as e:
            logger.exception(
                f"Error deleting Redis cache for key: {key}. Error: {str(e)}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal Server Error",
            )


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


def cache_lookup(
    key: str,
    db: Session,
    model,
    field: str,
    value: str,
    not_found_msg: str,
    result_key: str,
) -> dict:
    """
    Generic utility to check Redis cache first, then fallback to DB query if not found.
    If found in DB, it also caches the result in Redis for future lookups.
    """
    try:
        logger = AppLogger().get_logger()
        # First check Redis cache for the key
        redis = RedisCache()
        logger.info(f"Looking up key: {key} in Redis cache")
        cached = redis.get(key=key)
        # If found in cache, return immediately
        if cached:
            logger.info(f"Cache hit for key: {key}. Returning cached value.")
            return {"message": URL_EXISTS, result_key: cached}
        logger.info(f"Cache miss for key: {key}. Checking database...")
        record = get_record_by_field(
            db=db, model=model, field=field, value=value
        )
        #   If not found in DB, raise 404
        if not record:
            logger.exception(
                f"Cache miss for key: {key}. No record found in database."
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=not_found_msg
            )
        # If found in DB, cache the result and return it
        logger.info(
            f"Record found in database for key: {key}. Caching result and returning value."
        )
        result_value = getattr(record, result_key)
        # Cache the result in Redis for future lookups
        logger.info(
            f"Caching result for key: {key} with value: {result_value} in Redis"
        )
        redis.set(key=key, value=result_value)
        logger.info(
            f"Result cached successfully for key: {key}. Returning value."
        )
        return {"message": URL_EXISTS, result_key: result_value}
    except HTTPException as e:
        logger.exception(
            f"HTTPException occurred during cache lookup for key: {key}. Detail: {e.detail}"
        )
        raise e
    except Exception as e:
        logger.exception(
            f"Unexpected error during cache lookup for key: {key}. Error: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )
