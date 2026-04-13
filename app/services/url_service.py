from sqlalchemy.orm import Session
from app.config import (
    SHORT_URL,
    LONG_URL,
    URL_SHORTENED_ALREADY,
    URL_SHORTENED_SUCCESSFULLY,
    URL_DOESNT_EXIST,
)
from app.models import URLModel
from app.utils import (
    cache_lookup,
    get_record_by_field,
    shorten_text,
    RedisCache,
)
from app.utils import AppLogger
from fastapi import HTTPException, status

logger = AppLogger().get_logger()


def shorten_url(long_url: str, db: Session) -> dict:
    """
    Shorten a given long URL.
    """
    try:
        redis = RedisCache()
        logger.info(f"Attempting to shorten URL: {long_url}")
        short_url = redis.get(key=long_url)
        # If found in cache, return immediately
        if short_url:
            logger.info(f"Cache hit for URL: {long_url}")
            return {"message": URL_SHORTENED_ALREADY, "short_url": short_url}
        logger.info(f"Cache miss for URL: {long_url}. Checking database...")
        record = get_record_by_field(
            db=db, model=URLModel, field="long_url", value=long_url
        )
        #  If found in DB, cache the result and return it
        if record:
            redis.set(key=long_url, value=record.short_url)
            logger.info(
                f"URL found in database. Caching and returning short URL: {record.short_url}"
            )
            return {
                "message": URL_SHORTENED_ALREADY,
                "short_url": record.short_url,
            }
        # If not found in DB, create a new short URL, save it, cache it, and return it
        short_url = shorten_text(text=long_url)
        new_entry = URLModel(long_url=long_url, short_url=short_url)
        logger.info(
            f"Creating new short URL: {short_url} for long URL: {long_url}"
        )
        db.add(new_entry)
        logger.info(f"New short URL added to database session: {short_url}")
        db.commit()
        logger.info(f"Database commit successful for short URL: {short_url}")
        db.refresh(new_entry)
        logger.info(f"New short URL created and saved to database: {short_url}")
        # Cache the new short URL for future lookups
        logger.info(
            f"Caching new short URL: {short_url} for long URL: {long_url}"
        )
        redis.set(key=long_url, value=short_url)
        logger.info(f"Short URL created and cached successfully: {short_url}")
        return {"message": URL_SHORTENED_SUCCESSFULLY, "short_url": short_url}
    except Exception as e:
        logger.exception(
            f"Error occurred while shortening URL: {long_url}. Error: {str(e)}"
        )
        raise e


def get_shortened_url(long_url: str, db: Session) -> dict:
    """
    Retrieve the short URL for a given long URL if it exists.
    """
    try:
        logger.info(f"Retrieving short URL for long URL: {long_url}")
        return cache_lookup(
            key=long_url,
            db=db,
            model=URLModel,
            field=LONG_URL,
            value=long_url,
            not_found_msg=URL_DOESNT_EXIST,
            result_key=SHORT_URL,
        )
    except Exception as e:
        logger.exception(
            f"Error occurred while retrieving short URL for long URL: {long_url}. Error: {str(e)}"
        )
        raise e


def get_long_url(short_url: str, db: Session) -> dict:
    """
    Retrieve the long URL for a given short URL if it exists.
    """
    try:
        logger.info(f"Retrieving long URL for short URL: {short_url}")
        return cache_lookup(
            key=short_url,
            db=db,
            model=URLModel,
            field=SHORT_URL,
            value=short_url,
            not_found_msg=URL_DOESNT_EXIST,
            result_key=LONG_URL,
        )
    except Exception as e:
        logger.exception(
            f"Error occurred while retrieving long URL for short URL: {short_url}. Error: {str(e)}"
        )
        raise e


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
