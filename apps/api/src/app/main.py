import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.audit_middleware import AuditMiddleware
from app.core.config import settings
from app.db.demo_bootstrap import run_demo_bootstrap
from app.db.session import close_db, init_db
from app.routers import admin, auth, constituents, exports, groups, health, organisations, profile_write, segmentation, taxonomies

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    if settings.demo_seed:
        try:
            await run_demo_bootstrap()
        except Exception:
            logger.exception(
                "Demo bootstrap failed; serving with existing data. "
                "Fix DEMO_SEED/DEMO_PASSWORD/ENVIRONMENT and restart."
            )
    yield
    await close_db()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="IITGN Alumni & Donor CRM API",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

app.add_middleware(AuditMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix=settings.api_prefix, tags=["health"])
app.include_router(auth.router, prefix=f"{settings.api_prefix}/auth", tags=["auth"])
app.include_router(constituents.router, prefix=f"{settings.api_prefix}/constituents", tags=["constituents"])
app.include_router(
    profile_write.router,
    prefix=f"{settings.api_prefix}/constituents",
    tags=["constituents"],
)
app.include_router(
    segmentation.router,
    prefix=f"{settings.api_prefix}/constituents",
    tags=["constituents"],
)
app.include_router(
    taxonomies.router,
    prefix=f"{settings.api_prefix}/taxonomies",
    tags=["taxonomies"],
)
app.include_router(
    organisations.router,
    prefix=f"{settings.api_prefix}/organisations",
    tags=["organisations"],
)
app.include_router(
    groups.router,
    prefix=f"{settings.api_prefix}/groups",
    tags=["groups"],
)
app.include_router(
    exports.router,
    prefix=f"{settings.api_prefix}/exports",
    tags=["exports"],
)
app.include_router(admin.router, prefix=f"{settings.api_prefix}/admin", tags=["admin"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.debug)
