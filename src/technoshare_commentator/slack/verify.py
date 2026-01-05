import hmac
import hashlib
import time
from fastapi import Request, HTTPException
from ..config import get_settings

settings = get_settings()

async def verify_slack_signature(request: Request):
    """
    Verifies the X-Slack-Signature header.
    Raises HTTPException if invalid.
    """
    # 1. Grab headers
    timestamp = request.headers.get("X-Slack-Request-Timestamp")
    signature = request.headers.get("X-Slack-Signature")

    if not timestamp or not signature:
        raise HTTPException(status_code=400, detail="Missing Slack headers")

    # 2. Check timestamp freshness (replay attack prevention)
    if abs(time.time() - int(timestamp)) > 60 * 5:
        raise HTTPException(status_code=400, detail="Request timestamp too old")

    # 3. Compute our own signature
    body = await request.body()
    sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}".encode('utf-8')
    
    my_signature = "v0=" + hmac.new(
        settings.SLACK_SIGNING_SECRET.encode('utf-8'),
        sig_basestring,
        hashlib.sha256
    ).hexdigest()

    # 4. Compare
    if not hmac.compare_digest(my_signature, signature):
        raise HTTPException(status_code=401, detail="Invalid Slack signature")
