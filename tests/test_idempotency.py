import pytest
from technoshare_commentator.store.repo import Repo
from technoshare_commentator.store.db import init_db
from technoshare_commentator.config import get_settings
import sqlite3
import os

# Use an in-memory or temp DB for tests ideally
# But for simplicity we might just mock or use a test.db
# Let's simple check logic with a clean temp db if possible, but that requires overriding Settings.

@pytest.fixture
def clean_db(tmp_path):
    # Override global settings path?
    # Pydantic BaseSettings can be patched
    db_file = tmp_path / "test.db"
    
    import technoshare_commentator.store.db as db_module
    original_path = db_module.settings.DB_PATH
    db_module.settings.DB_PATH = str(db_file)
    
    init_db()
    Repo.settings = db_module.settings # Ensure repo sees it if it imported it
    
    yield
    
    db_module.settings.DB_PATH = original_path

def test_save_message_idempotency(clean_db):
    """
    WHY: Slack can send duplicate events (at least once delivery). We must process each unique message only once.
    HOW: 
        1. Call `save_message` with a fresh event.
        2. Call `save_message` again with the SAME event (same channel + ts).
    EXPECTED:
        1. First call returns True (saved).
        2. Second call returns False (duplicate).
    """
    event = {
        "channel": "C_TEST",
        "ts": "12345.6789",
        "user": "U_TEST",
        "text": "Hello http://example.com"
    }
    
    # First save: should be True (new)
    assert Repo.save_message(event) == True
    
    # Second save: should be False (duplicate)
    assert Repo.save_message(event) == False

def test_job_creation(clean_db):
    """
    WHY: Saving a message containing a link should queue a job for the worker.
    HOW:
        1. Save a message.
        2. Call `claim_next_job`.
    EXPECTED: 
        1. `claim_next_job` returns the job dict matching the message.
        2. Calling `claim_next_job` again returns None (because the first one is now 'processing').
    """
    event = {
        "channel": "C_TEST",
        "ts": "999.999",
        "user": "U_TEST",
        "text": "Hello http://example.com"
    }
    Repo.save_message(event)
    
    job = Repo.claim_next_job()
    assert job is not None
    assert job["message_ts"] == "999.999"
    assert job["channel_id"] == "C_TEST"
    
    # Claim again: should be None (status is processing)
    job2 = Repo.claim_next_job()
    assert job2 is None
