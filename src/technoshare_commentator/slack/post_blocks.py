"""Slack message payload builders.

Provides functions to build chat.postMessage payloads with mrkdwn formatting.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def build_mrkdwn_blocks(text: str) -> List[Dict[str, Any]]:
    """
    Build Block Kit payload that renders Slack mrkdwn properly.
    Posts the entire text as a single block (no splitting).
    """
    return [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": text},
        }
    ]


def build_post_payload(
    channel: str,
    text: str,
    thread_ts: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Payload for chat.postMessage.
    Posts as plain text with mrkdwn enabled (no blocks) to avoid 3000-char block limit.
    """
    payload: Dict[str, Any] = {
        "channel": channel,
        "text": text,
        "mrkdwn": True,  # Enable mrkdwn formatting in text field
        "unfurl_links": False,
        "unfurl_media": False,
    }
    if thread_ts:
        payload["thread_ts"] = thread_ts
    return payload
