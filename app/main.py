from fastapi import FastAPI, Request, Response
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from core.celery_app import celery_app
from api.routes import auth, images
from core.rate_limit import limiter

app = FastAPI(title='Image Processing Service')
app.state.limiter = limiter

def rate_limit_handler(request: Request, exc: Exception) -> Response:
    assert isinstance(exc, RateLimitExceeded)
    return _rate_limit_exceeded_handler(request, exc)

app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
app.add_middleware(SlowAPIMiddleware)

app.include_router(auth.router)
app.include_router(images.router)
