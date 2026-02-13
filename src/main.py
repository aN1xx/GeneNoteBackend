"""FastAPI application factory."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from src.config import settings
from src.infrastructure.kafka import close_kafka_producer, get_kafka_producer
from src.presentation.admin import init_admin
from src.presentation.api import api_router
from src.presentation.exceptions import register_exception_handlers

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Starting application...")
    try:
        await get_kafka_producer()
        logger.info("Kafka producer initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize Kafka producer: {e}")

    yield

    logger.info("Shutting down application...")
    await close_kafka_producer()
    logger.info("Kafka producer closed")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        # Указываем что за прокси работаем через HTTPS:
        root_path="",
    )

    # 🔒 Proxy Headers (ВАЖНО: должен быть первым!)
    app.add_middleware(
        ProxyHeadersMiddleware,  # type: ignore[arg-type]
        trusted_hosts=["*"],  # или конкретные IP nginx
    )

    # 🔐 Sessions (обязательно для SqlAdmin)
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.jwt_secret_key,
        max_age=3600,
        same_site="lax",
    )

    # 🌍 CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    try:
        from pathlib import Path

        import sqladmin
        from fastapi.staticfiles import StaticFiles

        sqladmin_static = Path(sqladmin.__file__).parent / "static"

        app.mount(
            "/static",
            StaticFiles(directory=sqladmin_static),
            name="static",
        )
    except Exception as e:
        logger.warning(f"SqlAdmin static not mounted: {e}")

    init_admin(app)

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        return {"status": "healthy"}

    return app


app = create_app()
