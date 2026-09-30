from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://aitf:aitf_secret@localhost:5432/aitf_db"
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""
    LLM_API_URL: str = "https://api.openai.com/v1"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "Qwen/Qwen3-8B"
    EMBEDDING_MODEL: str = "paraphrase-multilingual-mpnet-base-v2"
    UPLOAD_DIR: str = "./uploads"
    APP_ENV: str = "development"
    MAX_UPLOAD_SIZE_MB: int = 25
    CORS_ORIGINS: str = "*"

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
