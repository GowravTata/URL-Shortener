from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.services.url_service import (
    delete_short_url,
    shorten_url,
    get_long_url,
    get_short_code_analytics)
from app.schemas.url import ShortenRequest


url_router = APIRouter()


@url_router.post(
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


@url_router.get(
    "/{short_code}",
    summary="Get long URL",
    description="Retrieve the long URL for a given short URL if it " "exists",
)
async def gets_long_url(short_code: str, db: Session = Depends(get_db)) -> dict:
    return get_long_url(short_code=short_code, db=db)



@url_router.delete(
    "/{short_code}",
    summary="Delete Short URL",
    description="Delete a Short URL and its corresponding long URL from the database and cache",
)
async def deletes_short_url(
    short_code: str, db: Session = Depends(get_db)
) -> dict:
    return delete_short_url(short_code=short_code, db=db)




@url_router.get(
    "/info/{short_code}",
    summary="Get Short URL metadata",
    description="Retrieve information about a short URL, including its corresponding long URL and expiry date",
)
async def gets_short_code_info(
    short_code: str, db: Session = Depends(get_db)
) -> dict:
    return get_short_code_analytics(short_code=short_code, db=db)

@url_router.get("/analytics/{short_code}",    
    summary="Get Short URL Analytics",
    description="Retrieve analytics data for a given short URL, including click count and timestamps of clicks",
)
async def get_analytics(
    short_code: str, db: Session = Depends(get_db)
) -> dict:
    return get_short_code_analytics(short_code=short_code, db=db, analytics=True)
  