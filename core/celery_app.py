from celery import Celery

from core.config import settings

celery_app = Celery(
    'imgroc',
    broker=settings.redis_url,
    backend=settings.redis_url
)

celery_app.autodiscover_tasks(['core'])