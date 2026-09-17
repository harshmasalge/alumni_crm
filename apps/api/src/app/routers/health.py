from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    return {"status": "ok", "service": "IITGN Alumni & Donor CRM API"}


@router.get("/health/ready")
async def readiness_check() -> dict:
    return {"status": "ready"}