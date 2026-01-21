"""Configuration management for TechnoShare Commentator.

Loads settings from environment variables and .env file.
Provides access to Slack credentials, OpenAI API key, Langfuse settings, etc.
"""

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
    MODEL: str = Field("gpt-5.2", description="LLM model for analysis (env has priority)")
    LOG_LEVEL: str = "INFO"
    
    # Langfuse settings
    LANGFUSE_HOST: str = Field("http://localhost:3000", description="Langfuse server host URL")
    LANGFUSE_PUBLIC_KEY: str = Field("", description="Langfuse public key")
    LANGFUSE_SECRET_KEY: str = Field("", description="Langfuse secret key")
    LANGFUSE_ENABLED: bool = Field(True, description="Enable Langfuse tracing")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

@lru_cache()
def get_settings() -> Settings:
    return Settings()
