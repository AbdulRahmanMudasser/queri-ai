from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    GEMINI_API_KEY: str
    ENV: str = "development"
    EMBEDDING_PROVIDER: str = "local"

    # Model Configurations
    LLM_MODEL_NAME: str = "models/gemini-2.5-flash-lite"
    SIMILARITY_THRESHOLD: float = 0.35

    # Query Execution Limits
    MAX_ROW_LIMIT: int = 100
    STATEMENT_TIMEOUT_MS: int = 5000

    @field_validator("EMBEDDING_PROVIDER")
    @classmethod
    def validate_embedding_provider(cls, v: str) -> str:
        if v not in ("local", "gemini"):
            raise ValueError("EMBEDDING_PROVIDER must be 'local' or 'gemini'")
        return v

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v.startswith("postgresql+asyncpg://"):
            raise ValueError("DATABASE_URL must use the postgresql+asyncpg:// protocol")
        return v

    @field_validator("GEMINI_API_KEY")
    @classmethod
    def validate_gemini_api_key(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("GEMINI_API_KEY must not be empty")
        return v

    # Redis Configuration
    REDIS_URL: str

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()  # type: ignore[call-arg]
