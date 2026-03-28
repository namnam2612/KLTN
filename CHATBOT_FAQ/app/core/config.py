from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "AI FAQ"
    APP_ENV: str = "dev"
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 8000

    RAW_DIR: str = "data/raw"
    EXTRACTED_DIR: str = "data/extracted"
    CLEANED_DIR: str = "data/cleaned"
    CHUNKS_DIR: str = "data/chunks"
    INDEX_DIR: str = "data/indexes/chroma_db"

    EMBEDDING_MODEL: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()