from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_env: str = "development"
    app_secret: str = "change-me"
    local_single_user: bool = True
    local_single_user_email: str = "you@example.com"

    # Database
    database_url: str = "postgresql+psycopg://learning:change-me@postgres:5432/learning_os"

    # Redis / Celery
    redis_url: str = "redis://redis:6379/0"
    celery_task_always_eager: bool = False

    # Object storage
    s3_endpoint_url: str = "http://minio:9000"
    s3_public_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "change-me-too"
    s3_bucket_originals: str = "originals"
    s3_bucket_previews: str = "previews"
    s3_region: str = "local"
    s3_use_ssl: bool = False

    # Uploads
    max_upload_mb: int = 500
    max_pdf_pages: int = 3000
    allowed_upload_mime_types: list[str] = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "image/png",
        "image/jpeg",
        "image/webp",
    ]

    # AI / retrieval
    embedding_provider: str = "bge_m3"
    embedding_dimension: int = 1024
    ai_provider: str = "gemini"
    gemini_api_key: str = ""
    # Sensible working defaults, not a hardcoded requirement — override via
    # env if Google renames/retires these (blueprint section 21.1: the
    # model name lives in config, never in code).
    fast_model: str = "gemini-2.5-flash"
    reasoning_model: str = "gemini-2.5-pro"
    vision_model: str = "gemini-2.5-flash"
    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_model: str = ""

    # Feature flags
    enable_mineru: bool = False
    enable_gemini_multimodal_embedding: bool = False
    enable_irt: bool = False
    enable_neo4j: bool = False
    enable_audio_overview: bool = False

    # Planner (not exercised before Phase 8)
    planner_freeze_hours: int = 24
    planner_stability_days: int = 7
    target_retention: float = 0.90

    @field_validator("allowed_upload_mime_types", mode="before")
    @classmethod
    def _split_csv(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
