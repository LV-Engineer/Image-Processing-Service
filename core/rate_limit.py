from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from core.config import settings
from core.security import decode_access_token

def rate_limit_key(request: Request) -> str:
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer'):
        token = auth_header.removeprefix('Brearer ')
        try:
            return f'user:{decode_access_token(token)}'
        except Exception:
            pass
    return get_remote_address(request)

limiter = Limiter(key_func=rate_limit_key, storage_uri=settings.redis_url)