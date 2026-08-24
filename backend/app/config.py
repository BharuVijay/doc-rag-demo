from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data"
PDFS_DIR = DATA_DIR / "pdfs"
INDEX_PATH = DATA_DIR / "index.json"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR.parent / ".env", extra="ignore")

    openai_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"
    chat_model: str = "gpt-4o-mini"

    # Retrieval tuning
    top_k: int = 4
    confidence_low_threshold: float = 0.28
    confidence_high_threshold: float = 0.55


settings = Settings()
