from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    GEMINI_API_KEY: str
    ENV: str = "development"

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

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()  # type: ignore[call-arg]
