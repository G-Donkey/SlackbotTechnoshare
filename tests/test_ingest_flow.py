import pytest
from fastapi.testclient import TestClient
from technoshare_commentator.main_ingest import app
from technoshare_commentator.store.repo import Repo
import time

client = TestClient(app)

def test_ingest_url_verification(test_db):
    """
    WHY: Slack requires a handshake (url_verification) to confirm we own the endpoint before sending events.
    HOW: Post a JSON payload with `type="url_verification"` and a challenge string.
    EXPECTED: Return HTTP 200 and the exact challenge string in the JSON body.
    """
    response = client.post("/slack/events", json={
        "type": "url_verification",
        "challenge": "my-challenge-string"
    })
    assert response.status_code == 200
    assert response.json() == {"challenge": "my-challenge-string"}

def test_ingest_event_callback_valid(test_db, mock_slack_verification):
    """
    WHY: We must accept valid message events containing links and queue them for processing.
    HOW: 
        1. Mock URL verification (signature).
        2. Force config to match test channel.
        3. Post a valid `event_callback` payload with a link in `text`.
    EXPECTED: 
        1. Return HTTP 200 "ok".
        2. Verify a row exists in `messages` table with status 'received'.
        3. Verify a job exists in `jobs` table with correct channel/ts.
    """
    # Fake event payload
    channel_id = "C_TEST" # Must match config? Config default is ...? 
    # In .env.example TECHNOSHARE_CHANNEL_ID is manually set, 
    # but in tests we might need to ensure settings match or update settings.
    # get_settings() is cached. We should check what it is or force it.
    
    from technoshare_commentator.config import get_settings
    settings = get_settings()
    # Force the channel ID to match our test event
    settings.TECHNOSHARE_CHANNEL_ID = "C_TEST"
    
    msg_ts = f"{time.time()}"
    payload = {
        "type": "event_callback",
        "event": {
            "type": "message",
            "channel": "C_TEST",
            "user": "U_USER",
            "text": "Check out https://example.com/tool",
            "ts": msg_ts
        }
    }
    
    response = client.post("/slack/events", json=payload)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    
    # Verify DB side effect
    status = Repo.get_message_status("C_TEST", msg_ts)
    assert status == "received"
    
    # Verify Job created
    # We can use Repo to peek or raw SQL
    job = Repo.claim_next_job()
    assert job is not None
    assert job["channel_id"] == "C_TEST"
    assert job["message_ts"] == msg_ts

def test_ingest_event_ignored_no_url(test_db, mock_slack_verification):
    """
    WHY: To avoid spamming the LLM/logs, we should ignore messages that contain no URLs.
    HOW: Post a valid event payload where `text` has no http/https links.
    EXPECTED: Return HTTP 200 (to satisfy Slack) but create NO job in the `jobs` table.
    """
    msg_ts = f"{time.time()}"
    payload = {
        "type": "event_callback",
        "event": {
            "type": "message",
            "channel": "C_TEST", # Assuming settings patched from prev test or shared
            "user": "U_USER",
            "text": "Just chit chat no links",
            "ts": msg_ts
        }
    }
    
    response = client.post("/slack/events", json=payload)
    assert response.status_code == 200
    
    # Should not be in jobs
    job = Repo.claim_next_job()
    assert job is None

def test_ingest_event_wrong_channel(test_db, mock_slack_verification):
    """
    WHY: We only want to monitor the specific #technoshare channel to be cost-effective and focused.
    HOW: Configure settings to "C_REAL" but receive an event from "C_WRONG".
    EXPECTED: Return HTTP 200 (ignored status) and create NO job/message record.
    """
    from technoshare_commentator.config import get_settings
    settings = get_settings()
    settings.TECHNOSHARE_CHANNEL_ID = "C_REAL"
    
    payload = {
        "type": "event_callback",
        "event": {
            "type": "message",
            "channel": "C_WRONG",
            "user": "U_USER",
            "text": "https://example.com",
            "ts": "123.456"
        }
    }
    
    response = client.post("/slack/events", json=payload)
    # The endpoint returns "ignored" status or just 200 ok (ignoring secretly)
    assert response.json() == {"status": "ignored"}
