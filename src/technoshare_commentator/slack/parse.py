from typing import Dict, Any, Optional
from ..config import get_settings

settings = get_settings()

def parse_event(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Parse a Slack event payload. 
    Returns a simplified event dict if valid and relevant, else None.
    """
    event = payload.get("event", {})
    
    # 1. Filter by Channel
    channel = event.get("channel")
    if channel != settings.TECHNOSHARE_CHANNEL_ID:
        return None
        
    # 2. Ignore Bots
    if event.get("subtype") == "bot_message":
        return None
    if event.get("bot_id"):
        return None
        
    # 3. Ignore edits/deletions (for POC we only care about new messages)
    if event.get("subtype") in ["message_changed", "message_deleted"]:
        # If we want to handle edits later, logic goes here. Slack sends 'message' with subtype 'message_changed'
        return None
        
    # 4. Filter empty text (e.g. file-only posts? POC assumes links in text)
    text = event.get("text", "")
    if not text:
        return None

    return {
        "channel": channel,
        "ts": event.get("ts"),
        "thread_ts": event.get("thread_ts"), # if it's already in a thread
        "user": event.get("user"),
        "text": text
    }
