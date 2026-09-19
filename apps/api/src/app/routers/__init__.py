from fastapi import APIRouter

from app.routers import admin, auth, constituents, health, profile_write

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(constituents.router, prefix="/constituents", tags=["constituents"])
api_router.include_router(profile_write.router, prefix="/constituents", tags=["constituents"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])