from fastapi import FastAPI, Request, BackgroundTasks
from .config import get_settings
from .log import setup_logging, get_logger
from .store.db import init_db
from .store.repo import Repo
from .slack.verify import verify_slack_signature
from .slack.parse import parse_event
from .retrieval.url import extract_urls
from contextlib import asynccontextmanager

settings = get_settings()
setup_logging()
logger = get_logger("ingest")

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(lifespan=lifespan)

@app.post("/slack/events")
async def slack_events(request: Request, background_tasks: BackgroundTasks):
    # 1. Verify Signature
    await verify_slack_signature(request)
    
    # 2. Parse Body
    try:
        payload = await request.json()
    except Exception:
        return {"status": "error", "message": "Invalid JSON"}

    # 3. Handle URL Verification (Handshake)
    if payload.get("type") == "url_verification":
        return {"challenge": payload.get("challenge")}

    # 4. Handle Event Callback
    if payload.get("type") == "event_callback":
        event = parse_event(payload)
        if not event:
            return {"status": "ignored"}
            
        # Check for URLs immediately to decide if we even care
        urls = extract_urls(event["text"])
        if not urls:
            logger.info(f"No URLs in message {event['ts']}, ignoring.")
            return {"status": "ignored"}
            
        # Save to DB (Idempotency inside save_message)
        newly_saved = Repo.save_message(event)
        if newly_saved:
            logger.info(f"Queued job for message {event['ts']}")
        else:
            logger.info(f"Duplicate message {event['ts']}")
        
        return {"status": "ok"}

    return {"status": "ignored"}
