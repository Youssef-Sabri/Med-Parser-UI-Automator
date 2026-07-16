import hmac as hmac_mod
from fastapi import Header, HTTPException, status
from core.config import settings

async def get_api_key(x_api_key: str = Header(None)):
    """
    Validate the X-API-KEY header against the environment configuration.
    Uses constant-time comparison to prevent timing attacks.
    """
    valid_key = settings.MED_PARSER_API_KEY
    
    if not valid_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server misconfigured: API key not set."
        )
    if not x_api_key or not hmac_mod.compare_digest(x_api_key, valid_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key"
        )
    return x_api_key
