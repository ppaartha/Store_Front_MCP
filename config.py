"""Application configuration for the Customer & Order MCP project."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized environment-driven settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    postgres_user: str = Field(alias="POSTGRES_USER")
    postgres_password: str = Field(alias="POSTGRES_PASSWORD")
    postgres_db: str = Field(alias="POSTGRES_DB")
    postgres_host: str = Field(alias="POSTGRES_HOST", default="localhost")
    postgres_port: int = Field(alias="POSTGRES_PORT", default=5432)
    log_level: str = Field(alias="LOG_LEVEL", default="INFO")

    mcp_host: str = Field(alias="MCP_HOST", default="0.0.0.0")
    mcp_port: int = Field(alias="MCP_PORT", default=8000)
    mcp_transport: str = Field(alias="MCP_TRANSPORT", default="streamable-http")
    mcp_server_url: str = Field(alias="MCP_SERVER_URL", default="http://localhost:8000/mcp")

    openai_api_key: str = Field(alias="OPENAI_API_KEY", default="")
    openai_model: str = Field(alias="OPENAI_MODEL", default="gpt-5-mini")
    openai_temperature: float = Field(alias="OPENAI_TEMPERATURE", default=0.2)
    openai_max_retries: int = Field(alias="OPENAI_MAX_RETRIES", default=3)

    @property
    def database_url(self) -> str:
        """Build SQLAlchemy database URL."""
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor used across the app."""
    return Settings()
