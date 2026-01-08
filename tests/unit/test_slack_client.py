import pytest
from unittest.mock import MagicMock, patch
from slack_sdk.errors import SlackApiError

# We need to patch the WebClient inside slack/client.py
# Since slack_client is instantiated at module level, we patch 'technoshare_commentator.slack.client.SlackClientWrapper.client'

def test_post_reply_success():
    """
    WHY: Verify that our wrapper correctly calls the official Slack SDK with the right parameters.
    HOW: Mock the underlying `chat_postMessage` method. Call `post_reply` with sample data.
    EXPECTED: `chat_postMessage` should be called once with `channel`, `thread_ts`, and `text` exactly as passed.
    """
    from technoshare_commentator.slack.client import slack_client
    
    with patch.object(slack_client.client, 'chat_postMessage') as mock_post:
        mock_post.return_value = {"ok": True}
        
        slack_client.post_reply("C1", "123.456", "Hello World")
        
        mock_post.assert_called_once_with(
            channel="C1",
            thread_ts="123.456",
            text="Hello World",
            mrkdwn=True,
            unfurl_links=False,
            unfurl_media=False
        )

def test_post_reply_rate_limit_retry():
    """
    WHY: Slack APIs often rate limit bots. We need to ensure we retry automatically.
    HOW: Mock `chat_postMessage` to fail once with 'ratelimited' and then succeed.
    EXPECTED: `chat_postMessage` is called twice.
    """
    from technoshare_commentator.slack.client import slack_client
    
    # We need to mock the wait to make it fast
    with patch("time.sleep", return_value=None):
        with patch.object(slack_client.client, 'chat_postMessage') as mock_post:
            err = SlackApiError("ratelimited", {"ok": False, "error": "ratelimited"})
            mock_post.side_effect = [err, {"ok": True}]
            
            slack_client.post_reply("C1", "123", "Retry Me")
            
            assert mock_post.call_count == 2
