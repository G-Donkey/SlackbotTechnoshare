"""
Socket Mode event listener for TechnoShare Commentator.
Connects to Slack via WebSocket - no public URL needed.
"""
import logging
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from .config import get_settings
from .log import setup_logging
from .store.db import init_db
from .store.repo import Repo
from .retrieval.url import extract_urls

setup_logging()
logger = logging.getLogger("socket_listener")
settings = get_settings()

# Initialize Slack Bolt app with Socket Mode
app = App(
    token=settings.SLACK_BOT_TOKEN,
    # Socket Mode doesn't need signing secret for request verification
)

@app.event("message")
def handle_message_events(event, say, logger):
    """
    Handle incoming message events from Slack via Socket Mode.
    Filters and queues messages with URLs.
    """
    # Extract event data
    channel = event.get("channel")
    text = event.get("text", "")
    ts = event.get("ts")
    user = event.get("user")
    subtype = event.get("subtype")
    
    # Filter 1: Check channel
    if channel != settings.TECHNOSHARE_CHANNEL_ID:
        logger.debug(f"Ignoring message from channel {channel}")
        return
    
    # Filter 2: Ignore bot messages
    if subtype == "bot_message" or event.get("bot_id"):
        logger.debug("Ignoring bot message")
        return
    
    # Filter 3: Ignore message edits/deletions
    if subtype in ["message_changed", "message_deleted"]:
        logger.debug(f"Ignoring message subtype: {subtype}")
        return
    
    # Filter 4: Check for URLs
    urls = extract_urls(text)
    if not urls:
        logger.info(f"No URLs in message {ts}, ignoring.")
        return
    
    # Save to database (idempotent)
    event_data = {
        "channel": channel,
        "ts": ts,
        "thread_ts": event.get("thread_ts"),
        "user": user,
        "text": text
    }
    
    newly_saved = Repo.save_message(event_data)
    if newly_saved:
        logger.info(f"✓ Queued job for message {ts} (URL: {urls[0]})")
    else:
        logger.info(f"Duplicate message {ts}, skipped")

def main():
    """Start the Socket Mode handler."""
    logger.info("Starting Socket Mode listener...")
    logger.info(f"Monitoring channel: {settings.TECHNOSHARE_CHANNEL_ID}")
    
    # Initialize database
    init_db()
    
    # Start Socket Mode handler (blocks)
    handler = SocketModeHandler(app, settings.SLACK_APP_TOKEN)
    handler.start()

if __name__ == "__main__":
    main()
