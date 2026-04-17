from app.routes.url import url_router
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uuid
from app.exception_handlers import register_exception_handlers

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


@app.middleware("http")
async def request_context_and_rate_limit(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


register_exception_handlers(app)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


app.include_router(router=url_router)
