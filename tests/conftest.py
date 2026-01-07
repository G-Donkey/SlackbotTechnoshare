import pytest
import os
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch
from dotenv import load_dotenv

@pytest.fixture(scope="session", autouse=True)
def _load_env():
    # Load .env once per session to avoid side-effects on import time
    load_dotenv()

def _truthy(v: str | None) -> bool:
    return v is not None and v.strip().lower() not in ("", "0", "false", "no")

@pytest.fixture(scope="session")
def allow_integration(_load_env) -> bool:
    # Depends on _load_env to ensure .env is loaded first
    return _truthy(os.getenv("RUN_INTEGRATION_TESTS"))

@pytest.fixture(scope="session")
def openai_api_key(_load_env) -> str | None:
    key = os.getenv("OPENAI_API_KEY")
    if not key or key == "sk-...":
        return None
    return key

# Global setup to ensure we don't accidentally touch production DB

@pytest.fixture(scope="function")
def test_db(tmp_path):
    """
    Creates a temporary database for testing and initializes the schema.
    Patches the settings in `technoshare_commentator.config` and everywhere it's used if possible.
    """
    db_file = tmp_path / "test_technoshare.db"
    
    # We need to target where 'settings' is IMPORTED or used.
    # The most robust way for the `Repo` and `db` modules which import `settings` at top level
    # is to modify the `settings` object itself if it's a singleton.
    
    from technoshare_commentator.config import get_settings
    settings = get_settings()
    
    original_db_path = settings.DB_PATH
    settings.DB_PATH = str(db_file)
    
    # Initialize Schema
    from technoshare_commentator.store.db import init_db
    init_db()
    
    yield settings
    
    # Teardown
    settings.DB_PATH = original_db_path

@pytest.fixture
def mock_slack_verification():
    """
    Bypasses Slack signature verification for ingest tests.
    """
    with patch("technoshare_commentator.main_ingest.verify_slack_signature") as mock:
        # Make it an async no-op
        mock.return_value = None
        yield mock

@pytest.fixture
def mock_httpx():
    """
    Mocks httpx.Client for retrieval tests.
    """
    with patch("httpx.Client") as mock_client:
        yield mock_client
