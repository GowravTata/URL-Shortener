from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session 
from app.db import get_db
from app.services.url_service import shorten_url, get_shortened_url, get_long_url

db_router = APIRouter()

@db_router.get("/hello")
async def root():
    return {"message": "Hello World"}

@db_router.post("/shorten", 
                summary="Create short URL", 
                description="Convert a long URL into a short one")
async def shorten(long_url: str, db: Session = Depends(get_db))-> dict:
    return shorten_url(long_url=long_url, db=db)


@db_router.get("/shorten", 
                summary="Get short URL", 
                description="Retrieve the short URL for a given long URL if it exists")
async def shortened_url(long_url: str, db: Session = Depends(get_db))-> dict:
    return get_shortened_url(long_url=long_url, db=db)

@db_router.get("/long_url", 
                summary="Get long URL", 
                description="Retrieve the long URL for a given short URL if it exists")
async def gets_long_url(short_url: str, db: Session = Depends(get_db))-> dict:
    return get_long_url(short_url=short_url, db=db)
