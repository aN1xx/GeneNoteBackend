"""API v1 endpoints."""

from src.presentation.api.v1.endpoints.annotation import router as annotation_router
from src.presentation.api.v1.endpoints.auth import router as auth_router
from src.presentation.api.v1.endpoints.patients import router as patients_router
from src.presentation.api.v1.endpoints.pipelines import router as pipelines_router
from src.presentation.api.v1.endpoints.reports import router as reports_router
from src.presentation.api.v1.endpoints.samples import router as samples_router
from src.presentation.api.v1.endpoints.upload import router as upload_router
from src.presentation.api.v1.endpoints.variants import router as variants_router

__all__ = [
    "annotation_router",
    "auth_router",
    "patients_router",
    "pipelines_router",
    "reports_router",
    "samples_router",
    "upload_router",
    "variants_router",
]
