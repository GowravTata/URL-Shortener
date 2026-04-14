from typing import Annotated, AnyStr
from pydantic import BaseModel, ConfigDict


class ShortenRequest(BaseModel):
    long_url: AnyStr
    custom_alias: Annotated[
        str | None, "Optional custom alias for the short URL"
    ] = None
    expiry: Annotated[
        str | None, "Optional expiration time for the short URL"
    ] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "long_url": "https://www.amazon.com",
                "custom_alias": "az.com",
                "expiry": "2026-12-31T23:59:59",
            }
        }
    )
