"""Application configuration using Pydantic Settings (12-factor app)."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "GeneNote Backend"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: Literal["development", "staging", "production"] = "development"

    # API
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = Field(default=["http://localhost:3000"])

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/genenote"
    )
    database_echo: bool = False
    database_pool_size: int = 5
    database_max_overflow: int = 10

    # Kafka
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_consumer_group: str = "genenote-workers"

    # JWT
    jwt_secret_key: str = Field(default="your-secret-key-change-in-production")
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # File Storage
    file_storage_path: Path = Field(default=Path("/data/files"))
    max_upload_size_mb: int = 500  # FASTQ files can be large

    # PDF Generation
    pdf_font_path: Path | None = Field(
        default=None,
        description="Path to TTF font file with Cyrillic support. "
        "Recommended: SegoeUI (~/.fonts/segoeui/segoeui.ttf). "
        "If not set, will auto-detect system fonts.",
    )
    pdf_logo_path: Path | None = Field(
        default=None,
        description="Path to logo PDF file for report header. "
        "If not set, will use pipeline/src/olymp_logo.pdf if available.",
    )

    # Pipeline (Snakemake variant calling pipeline)
    pipeline_path: Path = Field(
        default=Path(
            "./pipeline"
        )
    )
    snakemake_cores: int = 4

    # Legacy snakemake settings (deprecated, use pipeline_path)
    snakemake_path: Path = Field(default=Path("./snakemake"))
    snakemake_conda_env: str = "snakemake"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Parse CORS origins from a comma-separated string, JSON array, or list."""
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            # Try to parse as JSON array first
            v_stripped = v.strip()
            if v_stripped.startswith("[") and v_stripped.endswith("]"):
                try:
                    parsed = json.loads(v_stripped)
                    if isinstance(parsed, list):
                        return [str(origin).strip() for origin in parsed]
                except json.JSONDecodeError:
                    pass
            # Fall back to comma-separated string
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @property
    def async_database_url(self) -> str:
        """Return async database URL string."""
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
