from celery_app import celery_app
from app.db import get_db
from app.models.url import URLModel
from app.utils import AppLogger
from datetime import datetime
from app.db import redis_conn as redis
from sqlalchemy import or_

logger = AppLogger().


@celery_app.task
def cleanup_expired_urls():
    """Celery task to clean up expired URLs from the database and Redis cache."""
    db = next(get_db())
    try:
        logger.info("Starting cleanup of expired URLs.")
        # Query for expired URLs
        expired_urls = (
            db.query(URLModel)
            .filter(
                or_(
                    URLModel.expires_at < datetime.now(),
                    URLModel.is_deleted.is_(True),
                )
            )
            .all()
        )
        for url in expired_urls:
            # Delete from Redis
            redis.delete(f"url:{url.short_code}")
            # Delete from database
            db.delete(url)
        db.commit()
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
    finally:
        logger.info("Finished cleanup of expired URLs.")
        db.close()
