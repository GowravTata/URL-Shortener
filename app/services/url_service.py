from sqlalchemy.orm import Session
from app.config import (
    SHORT_URL,
    URL_EXISTS,
    LONG_URL,
    URL_SHORTENED_SUCCESSFULLY,
    URL_DOESNT_EXIST,
)
from app.models.url import URLModel
from app.utils import (
    get_record_by_field,
    RedisCache,
    AppLogger,
    encode_base62,
    get_expiry_date,
)
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

logger = AppLogger().get_logger()


def shorten_url(
    long_url: str, short_url: str | None, expiry: str | None, db: Session
) -> dict:
    """
    Shorten a given long URL.
    """
    new_entry = None
    try:
        redis = RedisCache()
        logger.info(f"Shortening URL: {long_url}")

        if short_url:
            # If a custom short URL is provided, check if it already exists for this long URL
            # Check if the long URL already exists in the database
            short_url_record = get_record_by_field(
                db=db, model=URLModel, field=SHORT_URL, value=short_url
            )
            if short_url_record:
                logger.warning(
                    f"Custom Alias {short_url} already exists. Please choose a different custom alias."
                )
                raise HTTPException(
                    status_code=400,
                    detail={"message": "Custom Alias already exists"},
                )
                

        # Adding entry into the database
        new_entry = URLModel(long_url=long_url)
        db.add(new_entry)
        db.commit()
        db.refresh(new_entry)

        # If no custom short URL is provided, generate one using the entry ID
        if not short_url:
            short_url = encode_base62(new_entry.id)
            logger.info(
                f"Generated short URL: {short_url} for long URL: {long_url}"
            )

        # Parse expiry if provided, else set to 30 days from now
        expiry_dt = get_expiry_date(expiry)

        # Update the new entry with the short URL and expiry date, then commit the changes
        new_entry.short_url = short_url
        new_entry.expiry = expiry_dt
        db.commit()
        logger.info(f"Database commit successful for short URL: {short_url}")
        db.refresh(new_entry)
        logger.info(f"New short URL created and saved to database: {short_url}")
        # Cache the new short URL for future lookups
        logger.info(
            f"Caching new short URL: {short_url} for long URL: {long_url}"
        )
        redis.set(key=short_url, value=long_url, ex=86400)
        logger.info(f"Short URL created and cached successfully: {short_url}")
        return {"message": URL_SHORTENED_SUCCESSFULLY, "short_url": short_url}
    except (Exception, IntegrityError) as e:
        logger.exception(f"Error: {str(e)}")
        raise HTTPException(status_code=e.status_code, detail={"message": e.detail})


def get_long_url(short_url: str, db: Session) -> dict:
    """
    Retrieve the long URL for a given short URL if it exists.
    """
    try:
        logger = AppLogger().get_logger()
        # First check Redis cache for the key
        redis = RedisCache()
        logger.info(f"Looking up key: {short_url} in Redis cache")
        cached = redis.get(key=short_url)
        # If found in cache, return immediately
        if cached:
            logger.info(
                f"Cache hit for key: {short_url}. Returning cached value."
            )
            return {"message": URL_EXISTS, "long_url": cached}
        logger.info(f"Cache miss for key: {short_url}. Checking database...")
        record = get_record_by_field(
            db=db, model=URLModel, field=SHORT_URL, value=short_url
        )
        #   If not found in DB, raise 404
        if not record:
            logger.exception(
                f"Cache miss for key: {short_url}. No record found in database."
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=URL_DOESNT_EXIST
            )
        # If found in DB, cache the result and return it
        logger.info(
            f"Record found in database for key: {short_url}. Caching result and returning value."
        )
        result_value = getattr(record, LONG_URL)
        # Cache the result in Redis for future lookups
        logger.info(
            f"Caching result for key: {short_url} with value: {result_value} in Redis"
        )
        redis.set(key=short_url, value=result_value)
        logger.info(
            f"Result cached successfully for key: {short_url}. Returning value."
        )
        return {"message": URL_EXISTS, "long_url": result_value}
    except HTTPException as e:
        logger.exception(
            f"HTTPException occurred during cache lookup for key: {short_url}. Detail: {e.detail}"
        )
        raise e
    except Exception as e:
        logger.exception(
            f"Unexpected error during cache lookup for key: {short_url}. Error: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


def delete_long_url(long_url: str, db: Session) -> dict:
    """
    Delete a long URL and its corresponding short URL from the database and cache.
    """
    try:
        logger.info(f"Attempting to delete long URL: {long_url}")
        record = get_record_by_field(
            db=db, model=URLModel, field=LONG_URL, value=long_url
        )
        if not record:
            logger.exception(f"Long URL not found in database: {long_url}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=URL_DOESNT_EXIST,
            )
        short_url = record.short_url
        db.delete(record)
        db.commit()
        logger.info(f"Long URL deleted from database: {long_url}")
        redis = RedisCache()
        redis.delete(key=long_url)
        redis.delete(key=short_url)
        logger.info(
            f"Cache cleared for long URL: {long_url} and short URL: {short_url}"
        )
        return {"message": "URL deleted successfully"}
    except Exception as e:
        logger.exception(
            f"Error occurred while deleting long URL: {long_url}. Error: {str(e)}"
        )
        raise e
