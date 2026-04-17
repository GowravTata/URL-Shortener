from datetime import datetime

from fastapi import HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import (
    DOMAIN,
    SHORT_CODE,
    URL_SHORTENED_SUCCESSFULLY,
    URL_DOESNT_EXIST,
    URL_EXPIRED,
    SHORT_CODE_DOESNOT_EXIST,
)
from app.db import redis_conn as redis
from app.models.url import URLModel
from app.utils import (
    get_record_by_field,
    AppLogger,
    get_expiry_date,
    generate_code,
)
from urllib.parse import urlparse

logger = AppLogger().get_logger()


def shorten_url(
    long_url: str, custom_alias: str | None, expiry: str | None, db: Session
) -> dict:
    try:
        parsed = urlparse(long_url)
        if parsed.scheme not in ("http", "https"):
            logger.exception(f"Invalid URL scheme for URL: {long_url}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid URL scheme",
            )
        reserved_aliases = {"admin", "login", "signup", "dashboard"}
        if custom_alias and custom_alias in reserved_aliases:
            logger.exception(
                f"Custom alias '{custom_alias}' is reserved and cannot be used."
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Custom Alias is reserved. Please choose a different one.",
            )
        # Creating all the required variables for the new record
        expires_at = get_expiry_date(expiry)
        system_generated_code = generate_code()
        short_code = custom_alias or system_generated_code
        short_url = DOMAIN + short_code
        # Inserting the new record into the database
        created_at = datetime.utcnow().isoformat()
        new_entry = URLModel(
            long_url=long_url,
            short_code=short_code,
            short_url=short_url,
            expires_at=expires_at,
            created_at=created_at,
        )

        db.add(new_entry)
        logger.info(
            f"New URL entry added to database with short code: {short_code}"
        )
        db.commit()

        # Store all the data in a single Redis hash for efficient retrieval and management
        logger.info(
            f"Caching new URL entry in Redis with key: url:{short_code}"
        )
        redis.hset(
            f"url:{short_code}",
            mapping={
                "long_url": long_url,
                "expires_at": expires_at.isoformat(),
                "click_count": 0,
                "last_accessed": "",
                "is_deleted": 0,
                "created_at": created_at,
            },
        )
        ttl = expires_at and int(
            (expires_at - datetime.utcnow()).total_seconds()
        )

        if ttl:
            redis.expire(f"url:{short_code}", ttl)

        return {
            "message": URL_SHORTENED_SUCCESSFULLY,
            "short_url": short_url,
            "short_code": short_code,
        }

    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Custom Alias already exists",
        )
    except (Exception, HTTPException) as e:
        logger.exception(f"Error occurred while shortening URL: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


def get_long_url(short_code: str, db: Session) -> dict:
    """
    Retrieve the long URL for a given short URL if it exists.
    """
    try:
        # First check Redis cache for the key
        logger.info(f"Looking up key: {short_code} in Redis cache")
        key = f"url:{short_code}"
        cached = redis.hgetall(key)
        # If found in cache, return immediately
        if cached:
            logger.info(
                f"Cache hit for key: {short_code}. Returning cached value."
            )
            expires_at = cached.get("expires_at")
            if datetime.fromisoformat(expires_at) < datetime.utcnow():
                logger.exception(f"URL Expired in cache: {short_code}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail=URL_EXPIRED
                )

            # Since we stored a JSON string in Redis, we need to parse it back to a dictionary
            long_url = cached.get("long_url")
            pipe = redis.pipeline()
            pipe.hincrby(key, "click_count", 1)
            pipe.hset(key, "last_accessed", datetime.utcnow().isoformat())
            pipe.execute()
            return RedirectResponse(
                url=long_url, status_code=status.HTTP_302_FOUND
            )
        logger.info(f"Cache miss for key: {short_code}. Checking database...")
        record = get_record_by_field(
            db=db, model=URLModel, field=SHORT_CODE, value=short_code
        )
        #   If not found in DB, raise 404
        if not record:
            logger.exception(
                f"Cache miss for key: {short_code}. No record found in database."
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=URL_DOESNT_EXIST
            )
        if record and record.expires_at < datetime.utcnow():
            logger.exception(f"URL Expired in database: {short_code}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=URL_EXPIRED
            )

        if record.is_deleted:
            logger.exception(
                f"Short code marked as deleted in database: {short_code}"
            )
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail=SHORT_CODE_DOESNOT_EXIST,
            )
        # If found in DB, cache the result and return it
        logger.info(
            f"Record found in database for key: {record.short_url}. Caching result and returning value."
        )
        result_value = record.long_url
        # Cache the result in Redis for future lookups
        logger.info(
            f"Caching result for key: {short_code} with value: {result_value} in Redis"
        )
        ttl = (
            record.expires_at
            and int((record.expires_at - datetime.utcnow()).total_seconds())
            or 86400
        )
        # Store a JSON string in Redis with the long URL and expiry information, using the calculated TTL
        key = f"url:{short_code}"
        redis.hset(
            key,
            mapping={
                "long_url": result_value,
                "expires_at": (
                    record.expires_at.isoformat() if record.expires_at else None
                ),
                "last_accessed": datetime.utcnow().isoformat(),
                "click_count": 0,
                "is_deleted": 0,
                "created_at": record.created_at.isoformat(),
            },
        )
        if ttl and ttl > 0:
            redis.expire(key, ttl)

        logger.info(
            f"Result cached successfully for key: {short_code}. Returning value."
        )
        return RedirectResponse(
            url=result_value, status_code=status.HTTP_302_FOUND
        )
    except HTTPException as e:
        logger.exception(
            f"HTTPException occurred during cache lookup for key: {short_code}. Detail: {e.detail}"
        )
        raise e
    except Exception as e:
        logger.exception(
            f"Unexpected error during cache lookup for key: {short_code}. Error: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


def delete_short_url(short_code: str, db: Session) -> dict:
    """
    Delete a Short URL and its corresponding Long URL from the database and cache.
    """
    try:
        logger.info(f"Attempting to delete short URL: {short_code}")
        record = get_record_by_field(
            db=db, model=URLModel, field=SHORT_CODE, value=short_code
        )
        if not record:
            logger.exception(f"Short URL not found in database: {short_code}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=SHORT_CODE_DOESNOT_EXIST,
            )
        record.is_deleted = True
        db.commit()
        logger.info(f"Short URL deleted from database: {short_code}")
        logger.info(f"Cache cleared for short URL: {short_code}")
        redis.delete(f"url:{short_code}")
        return {"message": "URL deleted successfully"}
    except Exception as e:
        logger.exception(
            f"Error occurred while deleting short Code: {short_code}. Error: {str(e)}"
        )
        raise e


def get_short_code_info(short_code: str, db: Session) -> dict:
    """
    Retrieve the long URL and expiry information for a given short code if it exists.
    """
    try:
        logger.info(f"Retrieving info for short code: {short_code}")
        redis_short_code = f"url:{short_code}"
        cached = redis.hgetall(redis_short_code)
        if cached:
            logger.info(
                f"Cache hit for short code: {short_code}. Returning cached info."
            )
            if (
                datetime.fromisoformat(cached.get("expires_at"))
                < datetime.utcnow()
            ):
                logger.exception(f"URL Expired in cache: {short_code}")
                raise HTTPException(
                    status_code=status.HTTP_410_GONE, detail=URL_EXPIRED
                )

            return {
                "long_url": cached.get("long_url"),
                "created_at": cached.get("created_at"),
                "expiry": cached.get("expires_at"),
                "is_deleted": bool(int(cached.get("is_deleted"))),
            }
        record = get_record_by_field(
            db=db, model=URLModel, field=SHORT_CODE, value=short_code
        )
        if not record:
            logger.exception(f"Short code not found in database: {short_code}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=SHORT_CODE_DOESNOT_EXIST,
            )
        if record.is_deleted:
            logger.exception(
                f"Short code marked as deleted in database: {short_code}"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=SHORT_CODE_DOESNOT_EXIST,
            )
        if record.expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail=URL_EXPIRED,
            )
        return {
            "long_url": record.long_url,
            "created_at": record.created_at,
            "expiry": record.expires_at,
            "is_deleted": record.is_deleted,
        }
    except HTTPException as e:
        logger.exception(
            f"HTTPException occurred while retrieving info for short code: {short_code}. Detail: {e.detail}"
        )
        raise e
    except Exception as e:
        logger.exception(
            f"Unexpected error while retrieving info for short code: {short_code}. Error: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


def get_short_code_analytics(short_code: str, db: Session) -> dict:
    """
    Retrieve the long URL and expiry information for a given short code if it exists.
    """
    try:
        logger.info(f"Retrieving info for short code: {short_code}")
        redis_short_code = f"url:{short_code}"
        cached = redis.hgetall(redis_short_code)
        if cached:
            logger.info(
                f"Cache hit for short code: {short_code}. Returning cached info."
            )
            if (
                datetime.fromisoformat(cached.get("expires_at"))
                < datetime.utcnow()
            ):
                logger.exception(f"URL Expired in cache: {short_code}")
                raise HTTPException(
                    status_code=status.HTTP_410_GONE, detail=URL_EXPIRED
                )

            data = {
                "long_url": cached.get("long_url"),
                "created_at": cached.get("created_at"),
                "expiry": cached.get("expires_at"),
                "is_deleted": bool(int(cached.get("is_deleted"))),
                "click_count": cached.get("click_count"),
                "last_accessed": cached.get("last_accessed"),
            }
            return data
        record = get_record_by_field(
            db=db, model=URLModel, field=SHORT_CODE, value=short_code
        )
        if not record:
            logger.exception(f"Short code not found in database: {short_code}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=SHORT_CODE_DOESNOT_EXIST,
            )
        if record.is_deleted:
            logger.exception(
                f"Short code marked as deleted in database: {short_code}"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=SHORT_CODE_DOESNOT_EXIST,
            )
        if record.expires_at < datetime.utcnow():
            logger.exception(f"URL Expired in database: {short_code}")
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail=URL_EXPIRED,
            )
        return {
            "long_url": record.long_url,
            "click_count": record.click_count,
            "created_at": record.created_at,
            "expiry": record.expires_at,
            "last_accessed": record.last_accessed,
            "is_deleted": record.is_deleted,
        }
    except HTTPException as e:
        logger.exception(
            f"HTTPException occurred while retrieving info for short code: {short_code}. Detail: {e.detail}"
        )
        raise e
    except Exception as e:
        logger.exception(
            f"Unexpected error while retrieving info for short code: {short_code}. Error: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )
