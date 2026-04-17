from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.utils import _error_payload


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    payload = _error_payload(
        request,
        code="validation_error",
        message="Request validation failed",
    )
    payload["error"]["details"] = exc.errors()
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=payload,
    )


async def http_exception_handler(
    request: Request, exc: HTTPException
) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict):
        code = detail.get("code", "http_error")
        message = str(detail.get("message", "HTTP Error"))
    else:
        code = "http_error"
        message = str(detail)

    payload = _error_payload(
        request,
        code=code,
        message=message,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=payload,
    )


async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    payload = _error_payload(
        request,
        code="internal_error",
        message="Internal Server Error",
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=payload,
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
