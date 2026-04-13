from fastapi import FastAPI
from app.routes import db_router

app = FastAPI(
    title="URL Shortener API",
    description="A simple URL shortener API built with FastAPI",
    version="1.0.0",
)

app.include_router(router=db_router)
