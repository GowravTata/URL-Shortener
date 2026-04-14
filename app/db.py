from app.config import (
    POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_HOST,
    POSTGRES_PORT,
    REDIS_HOST, REDIS_PORT
)
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import redis

# Redis connection (production: configure password, SSL, and connection pool if
# needed)
redis_conn = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=0,
    decode_responses=True,
    # password=REDIS_PASSWORD,  # Uncomment if using Redis auth
    # ssl=True,  # Uncomment if using SSL
)

# Database URL (production: never hardcode credentials, always use env/config)
DATABASE_URL = (
    f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@"
    f"{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

# SQLAlchemy engine with production-ready settings
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Disable SQL echo in production
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db():
    """Create all tables. Run once at startup or via migration scripts."""
    Base.metadata.create_all(engine)


def get_db():
    """Dependency for getting a SQLAlchemy session.
    Use with FastAPI Depends."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
