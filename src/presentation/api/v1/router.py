"""API v1 main router."""

from fastapi import APIRouter

from src.presentation.api.v1.endpoints import (
    annotation_router,
    auth_router,
    patients_router,
    pipelines_router,
    reports_router,
    samples_router,
    upload_router,
    variants_router,
)

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth_router)
api_router.include_router(patients_router)
api_router.include_router(samples_router)
api_router.include_router(variants_router)
api_router.include_router(pipelines_router)
api_router.include_router(upload_router)
api_router.include_router(annotation_router)
api_router.include_router(reports_router)
