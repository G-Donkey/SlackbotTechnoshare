import pytest
import hmac
import hashlib
import time
from fastapi import Request, HTTPException
from technoshare_commentator.slack.verify import verify_slack_signature
from technoshare_commentator.config import get_settings

# Mock settings
settings = get_settings()

@pytest.mark.asyncio
async def test_verify_valid_signature():
    """
    WHY: Ensure we accept requests signed correctly with our secret.
    HOW: Generate valid signature using HMAC-SHA256 and current timestamp.
    EXPECTED: Function completes without raising HTTPException.
    """
    timestamp = str(int(time.time()))
    body = b'{"foo":"bar"}'
    
    sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}".encode('utf-8')
    signature = "v0=" + hmac.new(
        settings.SLACK_SIGNING_SECRET.encode('utf-8'),
        sig_basestring,
        hashlib.sha256
    ).hexdigest()
    
    # Mock Request
    scope = {
        "type": "http",
        "headers": [
            (b"x-slack-request-timestamp", timestamp.encode()),
            (b"x-slack-signature", signature.encode())
        ]
    }
    
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}
        
    request = Request(scope, receive)
    
    # Should not raise
    await verify_slack_signature(request)

@pytest.mark.asyncio
async def test_verify_invalid_signature():
    """
    WHY: Reject requests with bad signatures (security).
    HOW: Send junk signature.
    EXPECTED: Raise HTTPException 401.
    """
    timestamp = str(int(time.time()))
    body = b'{"foo":"bar"}'
    signature = "v0=invalid_signature"
    
    scope = {
        "type": "http",
        "headers": [
            (b"x-slack-request-timestamp", timestamp.encode()),
            (b"x-slack-signature", signature.encode())
        ]
    }
    
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}
        
    request = Request(scope, receive)
    
    with pytest.raises(HTTPException) as exc:
        await verify_slack_signature(request)
    assert exc.value.status_code == 401

@pytest.mark.asyncio
async def test_verify_stale_timestamp():
    """
    WHY: Prevent Replay Attacks where an attacker captures a valid request and resends it later.
    HOW: Send valid signature but timestamp is 10 minutes old.
    EXPECTED: Raise HTTPException 400.
    """
    timestamp = str(int(time.time()) - 600) # 10 mins ago
    body = b'{"foo":"bar"}'
    
    sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}".encode('utf-8')
    signature = "v0=" + hmac.new(
        settings.SLACK_SIGNING_SECRET.encode('utf-8'),
        sig_basestring,
        hashlib.sha256
    ).hexdigest()
    
    scope = {
        "type": "http",
        "headers": [
            (b"x-slack-request-timestamp", timestamp.encode()),
            (b"x-slack-signature", signature.encode())
        ]
    }
    
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}
        
    request = Request(scope, receive)
    
    with pytest.raises(HTTPException) as exc:
        await verify_slack_signature(request)
    assert exc.value.status_code == 400
