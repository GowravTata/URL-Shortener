from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import redis_conn, get_db
from app.models import URLModel
from app.utils import shorten_text  

db_router = APIRouter()

@db_router.get("/hello")
async def root():
    return {"message": "Hello World"}

@db_router.post("/shorten", summary="Create short URL", description="Convert a long URL into a short one")
async def shorten(long_url: str, db: Session = Depends(get_db)):
    short_url=redis_conn.get(long_url)
    if short_url:
        return {"message": "URL already shortened", "short_url": short_url}

    record = db.query(URLModel).filter_by(long_url=long_url).first()
    if record:
        redis_conn.set(long_url, record.short_url, ex=3600)
        return {"message": "URL already shortened", "short_url": record.short_url}

    short_url = shorten_text(long_url)
    new_entry = URLModel(long_url=long_url, short_url=short_url)
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    redis_conn.set(long_url, short_url)
    return {"message": "URL shortened successfully", "short_url": short_url}
    

@db_router.get("/shorten", summary="Get short URL", description="Retrieve the short URL for a given long URL if it exists")
async def gets_shortened_url(long_url: str, db: Session = Depends(get_db)):
    short_url = redis_conn.get(long_url)
    if short_url:
        return {"message": "URL Exists", "short_url": short_url}  

    record = db.query(URLModel).filter_by(long_url=long_url).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="URL Doesn't exist")
    short_url=record.short_url
    redis_conn.set(long_url, short_url, ex=3600)
    return {"message": "URL Exists", "short_url": short_url}


@db_router.get("/long_url", summary="Get long URL", description="Retrieve the long URL for a given short URL if it exists")
async def gets_long_url(short_url: str, db: Session = Depends(get_db)):
    long_url = redis_conn.get(short_url)
    if long_url:
        return {"message": "URL Exists", "long_url": long_url}

    record = db.query(URLModel).filter_by(short_url=short_url).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="URL Doesn't exist")
    long_url = record.long_url
    redis_conn.set(short_url, long_url, ex=3600)
    return {"message": "URL Exists", "long_url": long_url}