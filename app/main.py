from app.routes.url import url_router
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import time
import json
import uuid
from app.exception_handlers import register_exception_handlers
from app.utils import AppLogger

app = FastAPI(
    title="URL Shortener API",
    description="A simple URL shortener API built with FastAPI",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = AppLogger()


@app.middleware("http")
async def request_context_and_rate_limit(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start_time = time.perf_counter()
    request.state.request_id = request_id
    request.state.request_start_time = start_time

    response = await call_next(request)
    latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

    logger.info(
        json.dumps(
            {
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "latency_ms": latency_ms,
                "client_ip": request.client.host,
            }
        )
    )

    response.headers["X-Request-ID"] = request_id
    return response


register_exception_handlers(app)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


app.include_router(router=url_router)
