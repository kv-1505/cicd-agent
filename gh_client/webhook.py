import hmac
import hashlib
from fastapi import HTTPException, Request


async def verify_webhook_signature(request: Request, secret: str) -> bytes:
    """Validate GitHub webhook signature."""
    signature = request.headers.get("X-Hub-Signature-256")
    if not signature:
        raise HTTPException(status_code=401, detail="Missing webhook signature")

    body = await request.body()
    expected = "sha256=" + hmac.new(
        secret.encode(), body, hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    return body
