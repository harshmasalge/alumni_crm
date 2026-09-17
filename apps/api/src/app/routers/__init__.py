from fastapi import APIRouter

from app.routers import constituents, health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(constituents.router, prefix="/constituents", tags=["constituents"])