# wiring auth
from secrets import compare_digest
from fastapi import Header, HTTPException, status

from core.config import API_KEY

async def verify_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    if x_api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "Unauthorized",
                "message": "X-API-Key header required. Access denied.",
            },
        )
    
    elif not compare_digest(x_api_key, API_KEY):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "Unauthorized",
                "message": "Invalid API key provided. Access denied.",
            },
        )