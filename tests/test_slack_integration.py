import pytest
import os
from technoshare_commentator.slack.client import slack_client
from technoshare_commentator.config import get_settings

# These tests interact with REAL Slack. 
# They require SLACK_BOT_TOKEN and TECHNOSHARE_CHANNEL_ID in your .env or environment.

def is_token_set():
    try:
        s = get_settings()
        return s.SLACK_BOT_TOKEN and not s.SLACK_BOT_TOKEN.startswith("xoxb-...")
    except:
        return False

@pytest.mark.skipif(not is_token_set(), reason="SLACK_BOT_TOKEN not set or is placeholder")
def test_real_slack_read_history():
    """
    WHY: Verify that our token has the correct scopes to read messages.
    HOW: Call conversations.history on the configured channel.
    EXPECTED: Returns a list of messages.
    """
    settings = get_settings()
    channel_id = settings.TECHNOSHARE_CHANNEL_ID
    
    assert channel_id is not None, "TECHNOSHARE_CHANNEL_ID must be set for integration test"
    
    messages = slack_client.get_latest_messages(channel_id, limit=5)
    
    assert isinstance(messages, list)
    print(f"\nFetched {len(messages)} messages from {channel_id}")
    for msg in messages:
        print(f"- {msg.get('user', 'bot')}: {msg.get('text', '')[:50]}...")

@pytest.mark.skipif(not is_token_set(), reason="SLACK_BOT_TOKEN not set or is placeholder")
def test_real_slack_post_and_thread():
    """
    WHY: Verify we can actually post and thread in the real channel.
    HOW: 
        1. Post a top-level \"Integraton Test\" message.
        2. Post a threaded reply to it.
    EXPECTED: Both calls succeed.
    """
    settings = get_settings()
    channel_id = settings.TECHNOSHARE_CHANNEL_ID
    
    # 1. Post Top Level
    response = slack_client.client.chat_postMessage(
        channel=channel_id,
        text="[REAL_INTEGRATION_TEST] Starting test run..."
    )
    assert response["ok"] is True
    ts = response["ts"]
    
    # 2. Post Threaded Reply via our wrapper
    slack_client.post_reply(
        channel_id=channel_id,
        thread_ts=ts,
        text="[REAL_INTEGRATION_TEST] I can reply in a thread! ✅"
    )
    
    print(f"\nSuccessfully posted message {ts} and threaded reply.")
