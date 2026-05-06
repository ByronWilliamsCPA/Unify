"""Configuration settings for Foundry Unify."""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables (prefix: FOUNDRY_UNIFY_)."""

    model_config = SettingsConfigDict(
        env_prefix="foundry_unify_",
        case_sensitive=False,
        extra="ignore",
    )

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    json_logs: bool = False
    include_timestamp: bool = True

    # docling-serve connection
    docling_serve_url: str = Field(
        default="http://192.168.1.209:5001",
        description="Base URL for the docling-serve HTTP API",
    )
    docling_serve_timeout_seconds: float = Field(
        default=300.0,
        gt=0,
        description="Request timeout in seconds for docling-serve calls",
    )

    # KI-002 mitigation: Table confidence threshold
    layout_confidence_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Table detections below this confidence are reclassified to Text (KI-002)",
    )

    # GCS
    gcs_bucket_template: str = Field(
        default="rag-pipeline-{env}",
        description="GCS bucket name template; {env} is replaced with the request env value",
    )


settings = Settings()
