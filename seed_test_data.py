from datetime import datetime, timedelta

from app.config import DOMAIN
from app.db import SessionLocal
from app.db import redis_conn as redis
from app.models.url import URLModel


def build_dummy_rows() -> list[dict]:
    now = datetime.now()
    return [
        {
            "long_url": "https://docs.python.org/3/tutorial/",
            "short_code": "pyguide1",
            "expires_at": now + timedelta(days=60),
            "is_deleted": False,
            "click_count": 34,
            "last_accessed": now - timedelta(hours=5),
        },
        {
            "long_url": "https://fastapi.tiangolo.com/tutorial/",
            "short_code": "fastapi1",
            "expires_at": now + timedelta(days=45),
            "is_deleted": False,
            "click_count": 52,
            "last_accessed": now - timedelta(days=1, hours=2),
        },
        {
            "long_url": "https://redis.io/docs/latest/",
            "short_code": "redis101",
            "expires_at": now + timedelta(days=20),
            "is_deleted": False,
            "click_count": 19,
            "last_accessed": now - timedelta(hours=9),
        },
        {
            "long_url": "https://www.postgresql.org/docs/current/",
            "short_code": "pgdocs01",
            "expires_at": now + timedelta(days=30),
            "is_deleted": False,
            "click_count": 27,
            "last_accessed": now - timedelta(days=3),
        },
        {
            "long_url": "https://docs.celeryq.dev/en/stable/",
            "short_code": "celery01",
            "expires_at": now + timedelta(days=10),
            "is_deleted": False,
            "click_count": 13,
            "last_accessed": now - timedelta(days=2, hours=4),
        },
        {
            "long_url": "https://sqlalchemy.org/",
            "short_code": "ormguide",
            "expires_at": now - timedelta(days=2),
            "is_deleted": False,
            "click_count": 41,
            "last_accessed": now - timedelta(days=4),
        },
        {
            "long_url": "https://github.com/features/actions",
            "short_code": "ghaction",
            "expires_at": now - timedelta(hours=12),
            "is_deleted": False,
            "click_count": 7,
            "last_accessed": now - timedelta(days=1),
        },
        {
            "long_url": "https://developer.mozilla.org/en-US/docs/Web/HTTP",
            "short_code": "httpmdn",
            "expires_at": now + timedelta(days=90),
            "is_deleted": True,
            "click_count": 22,
            "last_accessed": now - timedelta(days=8),
        },
        {
            "long_url": "https://kubernetes.io/docs/home/",
            "short_code": "k8sdocs",
            "expires_at": now + timedelta(days=15),
            "is_deleted": True,
            "click_count": 5,
            "last_accessed": now - timedelta(days=6),
        },
        {
            "long_url": "https://www.cloudflare.com/learning/dns/what-is-dns/",
            "short_code": "dnslearn",
            "expires_at": now + timedelta(days=120),
            "is_deleted": False,
            "click_count": 64,
            "last_accessed": now - timedelta(hours=3),
        },
    ]


def seed_dummy_data() -> None:
    rows = build_dummy_rows()
    db = SessionLocal()

    try:
        short_codes = [row["short_code"] for row in rows]

        # Make script idempotent by removing only prior test rows for these short codes.
        db.query(URLModel).filter(URLModel.short_code.in_(short_codes)).delete(
            synchronize_session=False
        )
        db.commit()

        for row in rows:
            created_at = datetime.now() - timedelta(days=1)
            model = URLModel(
                long_url=row["long_url"],
                short_code=row["short_code"],
                short_url=f"{DOMAIN}{row['short_code']}",
                created_at=created_at,
                expires_at=row["expires_at"],
                last_accessed=row["last_accessed"],
                is_deleted=row["is_deleted"],
                click_count=row["click_count"],
            )
            db.add(model)

            redis.hset(
                f"url:{row['short_code']}",
                mapping={
                    "long_url": row["long_url"],
                    "expires_at": row["expires_at"].isoformat(),
                    "click_count": row["click_count"],
                    "last_accessed": row["last_accessed"].isoformat(),
                    "is_deleted": 1 if row["is_deleted"] else 0,
                    "created_at": created_at.isoformat(),
                },
            )

        db.commit()
        print(f"Inserted {len(rows)} dummy records into PostgreSQL and Redis.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_dummy_data()
