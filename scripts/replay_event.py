import asyncio
import httpx
import json
import time

URL = "http://localhost:3000/slack/events"
SECRET = "your-signing-secret" # Not used if we mock or if verification is disabled for debug, 
# but real verification needs headers.
# This script sends a raw payload assuming the server is running with signature verification DISABLED 
# OR we need to generate valid signatures.
# Since we implemented verify_slack_signature, we must generate a valid signature here.

import hmac
import hashlib
from technoshare_commentator.config import get_settings

settings = get_settings()

def generate_headers(body: bytes, timestamp: str):
    sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}".encode('utf-8')
    signature = "v0=" + hmac.new(
        settings.SLACK_SIGNING_SECRET.encode('utf-8'),
        sig_basestring,
        hashlib.sha256
    ).hexdigest()
    return {
        "X-Slack-Request-Timestamp": timestamp,
        "X-Slack-Signature": signature
    }

async def send_event(text_with_link: str):
    timestamp = str(int(time.time()))
    payload = {
        "type": "event_callback",
        "event": {
            "type": "message",
            "channel": settings.TECHNOSHARE_CHANNEL_ID,
            "user": "U12345",
            "text": text_with_link,
            "ts": f"{timestamp}.000100",
            "event_ts": f"{timestamp}.000100"
        }
    }
    
    body = json.dumps(payload).encode('utf-8')
    headers = generate_headers(body, timestamp)
    
    async with httpx.AsyncClient() as client:
        print(f"Sending event to {URL}...")
        resp = await client.post(URL, content=body, headers=headers)
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.text}")

if __name__ == "__main__":
    link = input("Enter link to test (default: https://openai.com): ") or "https://openai.com"
    asyncio.run(send_event(f"Check this out: {link}"))
