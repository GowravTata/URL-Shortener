from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.services.url_service import (
    delete_short_url,
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
        long_url=request.long_url,
        custom_alias=request.custom_alias,
        expiry=request.expiry,
        db=db,
    )


@db_router.get(
    "/{short_code}",
    summary="Get long URL",
    description="Retrieve the long URL for a given short URL if it " "exists",
)
async def gets_long_url(short_code: str, db: Session = Depends(get_db)) -> dict:
    return get_long_url(short_code=short_code, db=db)


@db_router.delete(
    "/{short_code}",
    summary="Delete Short URL",
    description="Delete a Short URL and its corresponding long URL from the database and cache",
)
async def deletes_short_url(
    short_code: str, db: Session = Depends(get_db)
) -> dict:
    return delete_short_url(short_url=short_code, db=db)
