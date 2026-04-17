from celery_app import celery_app
from datetime import datetime
from app.models.url import URLModel
from app.db import get_db
from app.utils import AppLogger
from app.db import redis_conn as redis


@celery_app.task
def flush_db():
    """Utility function to sync the click count from Redis to the database"""
    try:
        db = next(get_db())
        logger = AppLogger().get_logger()
        logger.info("Starting database flush to sync click counts.")
        # Fetch all keys that match the pattern "click:* and last_accessed:*"
        click_keys = db.query(URLModel).all()
        for record in click_keys:
            redis_key = f"click:{record.short_code}"
            cached = redis.hgetall(f"url:{record.short_code}")
            click_count = cached.get("click_count")
            last_accessed = cached.get("last_accessed")
            print(
                f"Printing from here, last access is {last_accessed} and click count is {click_count}"
            )
            updated = False
            if last_accessed:
                try:
                    # Redis stores ISO 8601 text; convert it to datetime for DB persistence.
                    record.last_accessed = datetime.fromisoformat(last_accessed)
                    updated = True
                except ValueError:
                    logger.warning(
                        f"Invalid last_accessed format for {record.short_code}: {last_accessed}"
                    )
                logger.info(
                    f"Synced last accessed for {record.short_code}: {last_accessed}"
                )
            if click_count:
                record.click_count = int(click_count)
                updated = True
                logger.info(
                    f"Synced click count for {record.short_code}: {click_count}"
                )

            if updated:
                db.commit()

    except Exception as e:
        logger.error(f"Error syncing click counts: {e}")
    finally:
        db.close()
