from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.services.url_service import (
    delete_long_url,
    shorten_url,
    get_long_url,
)
from app.schemas.url import ShortenRequest

db_router = APIRouter()


@db_router.get("/hello")
async def root():
    return {"message": "Hello World"}


@db_router.post(
    "/shorten",
    summary="Create short URL",
    description="Convert a long URL into a short one",
)
async def shorten(
    request: ShortenRequest, db: Session = Depends(get_db)
) -> dict:
    return shorten_url(
        long_url=request.long_url, short_url=request.custom_alias, expiry=request.expiry, db=db
    )


@db_router.get(
    "/long_url",
    summary="Get long URL",
    description="Retrieve the long URL for a given short URL if it " "exists",
)
async def gets_long_url(short_url: str, db: Session = Depends(get_db)) -> dict:
    return get_long_url(short_url=short_url, db=db)


@db_router.delete(
    "/delete_long_url",
    summary="Delete long URL",
    description="Delete a long URL and its corresponding short"
    " URL from the database and cache",
)
async def deletes_long_url(
    long_url: str, db: Session = Depends(get_db)
) -> dict:
    return delete_long_url(long_url=long_url, db=db)
