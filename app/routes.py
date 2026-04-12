from fastapi import APIRouter

db_router = APIRouter()

@db_router.get("/hello")
async def root():
    return {"message": "Hello World"}