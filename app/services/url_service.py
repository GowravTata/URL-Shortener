from fastapi import HTTPException, status
from sqlalchemy.orm import Session  
from app.config import (URL_SHORTENED_ALREADY,
                         URL_SHORTENED_SUCCESSFULLY, 
                         URL_EXISTS, 
                         URL_DOESNT_EXIST)
from app.models import URLModel
from app.utils import get_record_by_field,shorten_text, RedisCache

def shorten_url(long_url: str, db: Session):
    redis=RedisCache()
    short_url = redis.get(key=long_url)
    if short_url:
        return {"message": URL_SHORTENED_ALREADY, "short_url": short_url}
    record = get_record_by_field(db=db, model=URLModel, field='long_url', value=long_url)   
    if record:
        redis.set(key=long_url, value=record.short_url, ex=3600)
        return {"message": URL_SHORTENED_ALREADY, "short_url": record.short_url}

    short_url = shorten_text(long_url=long_url)
    new_entry = URLModel(long_url=long_url, short_url=short_url)
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    redis.set(key=long_url, value=short_url)
    return {"message": URL_SHORTENED_SUCCESSFULLY, "short_url": short_url}

def get_shortened_url(long_url: str, db: Session):
    redis=RedisCache()
    short_url = redis.get(key=long_url)
    if short_url:
        return {"message": URL_EXISTS, "short_url": short_url}

    record = get_record_by_field(db=db, model=URLModel, field='long_url', value=long_url)   
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=URL_DOESNT_EXIST)
    short_url = record.short_url
    redis.set(key=long_url, value=short_url, ex=3600)
    return {"message": URL_EXISTS, "short_url": short_url}

def get_long_url(short_url: str, db: Session):
    redis=RedisCache()
    long_url = redis.get(key=short_url)
    if long_url:
        return {"message": URL_EXISTS, "long_url": long_url}

    record = get_record_by_field(db, URLModel, 'short_url', short_url)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=URL_DOESNT_EXIST)
    long_url = record.long_url
    redis.set(key=short_url, value=long_url, ex=3600)
    return {"message": URL_EXISTS, "long_url": long_url}
