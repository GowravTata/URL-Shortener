from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ShortenRequest(BaseModel):
    long_url: HttpUrl
    custom_alias: Annotated[
        str | None,
        Field(
            default=None,
            min_length=3,
            max_length=32,
            pattern=r"^[A-Za-z0-9_-]+$",
            description="Optional custom alias for the short URL",
        ),
    ] = None
    expiry: Annotated[
        datetime | None,
        Field(
            default=None,
            description="Optional expiration datetime in ISO format",
        ),
    ] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "long_url": "https://www.amazon.com",
                "custom_alias": "amz",
                "expiry": "2026-04-30T23:59:59",
            }
        }
    )
