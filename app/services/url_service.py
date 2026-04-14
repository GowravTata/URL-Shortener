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
    encode_base62,
    get_expiry_date,
)
from datetime import datetime
from fastapi import HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError

logger = AppLogger().get_logger()


def shorten_url(
    long_url: str, custom_alias: str | None, expiry: str | None, db: Session
) -> dict:
    """
    Shorten a given long URL.
    """
    new_entry = None
    try:
        redis = RedisCache()
        logger.info(f"Shortening URL: {long_url}")

        if custom_alias:
            # If a custom short code is provided, check if it already exists for this long URL
            # Check if the long URL already exists in the database
            short_code_record = get_record_by_field(
                db=db, model=URLModel, field=SHORT_CODE, value=custom_alias
            )
            if short_code_record:
                logger.warning(
                    f"Custom Alias {custom_alias} already exists. Please choose a different custom alias."
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"message": "Custom Alias already exists"},
                )

        # Adding entry into the database
        new_entry = URLModel(long_url=long_url)
        db.add(new_entry)
        db.commit()
        db.refresh(new_entry)

        # If no custom short URL is provided, generate one using the entry ID
        if not custom_alias:
            short_code = encode_base62(new_entry.id)
            logger.info(
                f"Generated short code: {short_code} for long URL: {long_url}"
            )

        # Parse expiry if provided, else set to 30 days from now
        expiry_dt = get_expiry_date(expiry)

        # Creating the short URL and updating the database entry
        short_url = DOMAIN + (custom_alias if custom_alias else short_code)
        short_code = custom_alias if custom_alias else short_code
        # Update the new entry with the short URL and expiry date, then commit the changes
        new_entry.short_code = short_code
        new_entry.short_url = short_url
        new_entry.expiry = expiry_dt
        db.commit()
        db.refresh(new_entry)
        logger.info(f"Database commit successful for Short URL: {short_code}")

        # Cache the new short code for future lookups
        logger.info(
            f"Caching new short URL: {short_url} for long URL: {long_url}"
        )
        redis.set(key=short_code, value=long_url, ex=86400)
        logger.info(f"Short URL created and cached successfully: {short_code}")
        return {
            "message": URL_SHORTENED_SUCCESSFULLY,
            "short_url": short_url,
            "short_code": short_code,
        }
    except (Exception, IntegrityError) as e:
        logger.exception(f"Error: {str(e)}")
        raise e


def get_long_url(short_code: str, db: Session) -> dict:
    """
    Retrieve the long URL for a given short URL if it exists.
    """
    try:
        logger = AppLogger().get_logger()
        # First check Redis cache for the key
        redis = RedisCache()
        logger.info(f"Looking up key: {short_code} in Redis cache")
        cached = redis.get(key=short_code)
        # If found in cache, return immediately
        if cached:
            logger.info(
                f"Cache hit for key: {short_code}. Returning cached value."
            )
            return RedirectResponse(
                url=cached, status_code=status.HTTP_302_FOUND
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
        if record and record.expiry < datetime.now():
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
        redis.set(key=short_code, value=result_value, ex=86400)
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
            "created_at": record.created_at.isoformat(),
            "expiry": record.expiry.isoformat() if record.expiry else None,
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
