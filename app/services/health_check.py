from fastapi import status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from app.db import SessionLocal, redis_conn
from app.utils import _error_payload


def db_readiness() -> JSONResponse:
    """Endpoint to check the health of the database and Redis connections."""
    db_ok = False
    redis_ok = False
    # Check database connectivity
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    finally:
        db.close()
    # Check Redis connectivity
    try:
        redis_conn.ping()
        redis_ok = True
    except Exception:
        redis_ok = False
    # Construct response
    payload = {
        "status": "ready" if db_ok and redis_ok else "not_ready",
        "checks": {"database": db_ok, "redis": redis_ok},
    }
    status_code = (
        status.HTTP_200_OK
        if db_ok and redis_ok
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )
    return JSONResponse(status_code=status_code, content=payload)
