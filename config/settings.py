"""Centralized application and system configuration using Pydantic BaseSettings."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration settings for Remote 150K+ DS/AI/ML Job Search Platform."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    environment: str = Field(default="development", alias="ENVIRONMENT")
    app_name: str = Field(
        default="Remote 150K+ DS/AI/ML Job Search Platform", alias="APP_NAME"
    )
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")

    # Relational & Vector DB (PostgreSQL / pgvector)
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/jobs",
        alias="DATABASE_URL",
    )
    sync_database_url: str = Field(
        default="postgresql+psycopg2://postgres:postgres@localhost:5432/jobs",
        alias="SYNC_DATABASE_URL",
    )
    db_pool_size: int = Field(default=10, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, alias="DB_MAX_OVERFLOW")
    db_pool_pre_ping: bool = Field(default=True, alias="DB_POOL_PRE_PING")

    # In-Memory Store & Streams (Dragonfly)
    dragonfly_url: str = Field(
        default="redis://localhost:6379/0", alias="DRAGONFLY_URL"
    )
    stream_name: str = Field(default="raw-jobs", alias="STREAM_NAME")
    stream_group: str = Field(default="jobs-ingest", alias="STREAM_GROUP")
    stream_consumer: str = Field(default="consumer-1", alias="STREAM_CONSUMER")
    stream_maxlen: int = Field(default=100000, alias="STREAM_MAXLEN")
    dlq_stream_name: str = Field(default="raw-jobs-dlq", alias="DLQ_STREAM_NAME")

    # Search Engine (Elasticsearch)
    elasticsearch_url: str = Field(
        default="http://localhost:9200", alias="ELASTICSEARCH_URL"
    )
    es_index: str = Field(default="jobs", alias="ES_INDEX")
    es_username: str | None = Field(default=None, alias="ES_USERNAME")
    es_password: str | None = Field(default=None, alias="ES_PASSWORD")

    # Object Storage (MinIO)
    minio_endpoint: str = Field(default="localhost:9000", alias="MINIO_ENDPOINT")
    minio_access_key: str = Field(default="minioadmin", alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(default="minioadmin", alias="MINIO_SECRET_KEY")
    minio_bucket: str = Field(default="raw-jobs", alias="MINIO_BUCKET")
    minio_secure: bool = Field(default=False, alias="MINIO_SECURE")

    # Master Data & Dictionaries
    dictionary_dir: str = Field(
        default=os.getenv("DICTIONARY_DIR", "data/dictionaries"),
        alias="DICTIONARY_DIR",
    )

    # Security & Authentication
    jwt_secret: str = Field(
        default="change-in-production-job-search-secret-key-32chars",
        alias="JWT_SECRET",
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expiry_minutes: int = Field(default=60, alias="JWT_EXPIRY_MINUTES")

    # GenAI & Models
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    default_llm_provider: str = Field(default="openai", alias="DEFAULT_LLM_PROVIDER")
    default_embedding_provider: str = Field(
        default="openai", alias="DEFAULT_EMBEDDING_PROVIDER"
    )
    openai_embedding_model: str = Field(
        default="text-embedding-3-small", alias="OPENAI_EMBEDDING_MODEL"
    )
    embedding_dimension: int = Field(default=1536, alias="EMBEDDING_DIMENSION")
    local_embedding_model: str = Field(
        default="all-MiniLM-L6-v2", alias="LOCAL_EMBEDDING_MODEL"
    )

    # Feature Flags
    use_llm_skill_extraction: bool = Field(
        default=False, alias="USE_LLM_SKILL_EXTRACTION"
    )
    use_vector_search: bool = Field(default=False, alias="USE_VECTOR_SEARCH")
    enable_guardrails: bool = Field(default=False, alias="ENABLE_GUARDRAILS")

    def __init__(self, **values: Any):
        super().__init__(**values)
        self._load_feature_flags_file()

    def _load_feature_flags_file(self) -> None:
        """Load feature flags overrides from feature_flags.yaml if present."""
        flags_file = Path(__file__).parent / "feature_flags.yaml"
        if flags_file.exists():
            try:
                with open(flags_file, encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                if "use_llm_skill_extraction" in data and "USE_LLM_SKILL_EXTRACTION" not in os.environ:
                    self.use_llm_skill_extraction = bool(data["use_llm_skill_extraction"])
                if "use_vector_search" in data and "USE_VECTOR_SEARCH" not in os.environ:
                    self.use_vector_search = bool(data["use_vector_search"])
                if "enable_guardrails" in data and "ENABLE_GUARDRAILS" not in os.environ:
                    self.enable_guardrails = bool(data["enable_guardrails"])
            except Exception:
                pass


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached singleton application settings."""
    return Settings()
