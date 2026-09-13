from typing import Any
from core.celery_app import celery_app
from core.storage import download_file, upload_file
from core.transforms import apply_transforms
from core.cache import set_cached
from db.session import SessionLocal
from models.image import Image
from models.user import User  # noqa: F401 -- must be imported so SQLAlchemy can resolve images.owner_id's FK to users.id
from schemas.image import TransformRequest, ImageResponse

@celery_app.task(name='transform_image_task')
def transform_image_task(image_id: int, payloas_data: dict[str, Any], user_id: int, cache_key: str) -> int:
    db = SessionLocal()
    try:
        source = db.query(Image).filter(Image.id == image_id).first()
        if source is None:
            raise ValueError(f'Image {image_id} not found')

        payload = TransformRequest(**payloas_data)
        origin_bytes = download_file(source.s3_key)
        result = apply_transforms(origin_bytes, payload)

        from uuid import uuid4
        new_key = f'{user_id}/{uuid4()}'
        upload_file(new_key, result.data, result.content_type)

        new_image = Image(
            owner_id=user_id,
            s3_key=new_key,
            original_filename=source.original_filename,
            content_type=result.content_type,
            width=result.width,
            height=result.height,
            size_bytes=len(result.data),
            parent_image_id=source.id,
        )
        db.add(new_image)
        db.commit()
        db.refresh(new_image)

        response = ImageResponse.model_validate(new_image)
        set_cached(cache_key, response.model_dump(mode='json'))
        return new_image.id
    finally:
        db.close()