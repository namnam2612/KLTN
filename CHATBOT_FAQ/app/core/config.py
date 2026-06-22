from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "AI FAQ"
    APP_ENV: str = "dev"
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:3000"

    RAW_DIR: str = "data/raw"
    EXTRACTED_DIR: str = "data/extracted"
    CLEANED_DIR: str = "data/cleaned"
    CHUNKS_DIR: str = "data/chunks"
    INDEX_DIR: str = "data/indexes/chroma_db"
    CHAT_DB_PATH: str = "data/indexes/chat_db.sqlite3"

    EMBEDDING_MODEL: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


def ensure_runtime_dirs() -> None:
    for dir_path in [
        Path(settings.RAW_DIR),
        Path(settings.EXTRACTED_DIR),
        Path(settings.CLEANED_DIR),
        Path(settings.CHUNKS_DIR),
        Path(settings.INDEX_DIR),
        Path(settings.CHAT_DB_PATH).parent,
    ]:
        dir_path.mkdir(parents=True, exist_ok=True)


settings = Settings()
ensure_runtime_dirs()
