from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from functools import lru_cache
import yaml
from pathlib import Path
from typing import Dict, Any

class Settings(BaseSettings):
    SLACK_BOT_TOKEN: str = Field(..., description="Slack Bot User OAuth Token")
    SLACK_APP_TOKEN: str = Field(..., description="Slack App-Level Token (for Socket Mode)")
    TECHNOSHARE_CHANNEL_ID: str = Field(..., description="Channel ID to monitor")
    OPENAI_API_KEY: str = Field(..., description="OpenAI API Key")
    DB_PATH: str = Field("./db.sqlite", description="Path to SQLite database")
    MAX_LINKS_PER_MESSAGE: int = 3
    MODEL_STAGE_A: str = "gpt-4o"
    MODEL_STAGE_B: str = "gpt-4o"
    LOG_LEVEL: str = "INFO"
    
    # MLflow settings
    MLFLOW_TRACKING_URI: str = Field("http://127.0.0.1:5000", description="MLflow tracking server URI")
    MLFLOW_EXPERIMENT_NAME: str = Field("technoshare_commentator", description="MLflow experiment name")
    MLFLOW_ENABLE_TRACKING: bool = Field(True, description="Enable MLflow tracking")
    MLFLOW_ENABLE_TRACING: bool = Field(True, description="Enable MLflow tracing")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

@lru_cache()
def get_settings() -> Settings:
    return Settings()

def load_project_context() -> Dict[str, Any]:
    path = Path("data/project_context.yaml")
    if not path.exists():
        return {}
    with open(path, "r") as f:
        return yaml.safe_load(f)

def load_domain_rules() -> Dict[str, Any]:
    path = Path("data/domain_rules.yaml")
    if not path.exists():
        return {}
    with open(path, "r") as f:
        return yaml.safe_load(f)
