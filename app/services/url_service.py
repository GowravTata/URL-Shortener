from sqlalchemy.orm import Session
from app.config import (
    DOMAIN,
    SHORT_CODE,
    URL_SHORTENED_SUCCESSFULLY,
    URL_DOESNT_EXIST,
    URL_EXPIRED,
    SHORT_CODE_DOESNOT_EXIST,
)
from app.models.url import URLModel
from app.utils import (
    get_record_by_field,
    RedisCache,
    AppLogger,
    get_expiry_date,
)
from app.db import redis_conn as redis
from datetime import datetime
from fastapi import HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError
from app.utils import generate_code
import json

logger = AppLogger().get_logger()


def shorten_url(
    long_url: str, custom_alias: str | None, expiry: str | None, db: Session
) -> dict:
    try:
        redis = RedisCache()
        # Creating all the required variables for the new record
        expires_at = get_expiry_date(expiry)
        system_generated_code = generate_code()
        short_code = custom_alias or system_generated_code
        short_url = DOMAIN + short_code
        # Inserting the new record into the database
        new_entry = URLModel(
            long_url=long_url,
            short_code=short_code,
            short_url=short_url,
            expires_at=expires_at,
        )

        db.add(new_entry)
        db.commit()

        # Store a JSON string in Redis with the long URL and expiry information
        redis.set(
            f"url:{short_code}", json.dumps({"long_url": long_url}), ex=86400
        )
        # Setting the click count to 0 in Redis
        # with an expiration time of 24 hours (86400 seconds)
        redis.set(f"click:{short_code}", 0, ex=86400)

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
    except Exception as e:
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
        logger = AppLogger().get_logger()
        # First check Redis cache for the key
        logger.info(f"Looking up key: {short_code} in Redis cache")
        key = f"url:{short_code}"
        cached = redis.get(key)
        # If found in cache, return immediately
        if cached:
            logger.info(
                f"Cache hit for key: {short_code}. Returning cached value."
            )
            # Since we stored a JSON string in Redis, we need to parse it back to a dictionary
            json_data = json.loads(cached)
            long_url = json_data.get("long_url")
            redis.incr(f"click:{short_code}")
            record = get_record_by_field(
                db=db, model=URLModel, field=SHORT_CODE, value=short_code
            )
            if record:
                record.click_count += 1
                db.commit()
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
        if record and record.expires_at < datetime.now():
            logger.exception(f"URL Expired in database: {short_code}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=URL_EXPIRED
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
        redis.set(
            f"url:{short_code}", json.dumps({"long_url": result_value}), ex=ttl
        )
        # Setting the click count to 0 in Redis with an expiration time of 24 hours (86400 seconds)
        redis.set(f"click:{short_code}", 0, ex=86400)
        logger.info(
            f"Result cached successfully for key: {short_code}. Returning value."
        )
        return RedirectResponse(
            url=result_value, status_code=status.HTTP_302_FOUND
        )
        # return {"message": URL_EXISTS, "long_url": result_value}
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


def get_short_code_info(short_code: str, db: Session) -> dict:
    """
    Retrieve the long URL and expiry information for a given short code if it exists.
    """
    try:
        logger.info(f"Retrieving info for short code: {short_code}")
        record = get_record_by_field(
            db=db, model=URLModel, field=SHORT_CODE, value=short_code
        )
        if not record:
            logger.exception(f"Short code not found in database: {short_code}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=SHORT_CODE_DOESNOT_EXIST,
            )
        return {
            "long_url": record.long_url,
            "click_count": record.click_count,
            "created_at": record.created_at.isoformat(),
            "expiry": (
                record.expires_at.isoformat() if record.expires_at else None
            ),
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
        db.delete(record)
        db.commit()
        logger.info(f"Short URL deleted from database: {short_code}")
        redis = RedisCache()
        logger.info(f"Cache cleared for short URL: {short_code}")

        redis.delete(key=short_code)
        return {"message": "URL deleted successfully"}
    except Exception as e:
        logger.exception(
            f"Error occurred while deleting short Code: {short_code}. Error: {str(e)}"
        )
        raise e
