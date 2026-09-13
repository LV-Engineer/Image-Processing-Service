from io import BytesIO
from uuid import uuid4

from fastapi import APIRouter, Request, Depends, File, HTTPException, Query, UploadFile, status
from PIL import Image as PILImage
from sqlalchemy.orm import Session

from api.deps import get_current_user
from core.cache import get_cached, make_cache_key
from core.celery_app import celery_app
from core.rate_limit import limiter
from core.storage import delete_file, upload_file
from core.tasks import transform_image_task
from db.session import get_db
from models.image import Image
from models.user import User
from schemas.image import ImageListResponse, ImageResponse, TransformRequest, TransformJobResponse

router = APIRouter(prefix='/images', tags=['images'])

@router.post('', response_model=ImageResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit('30/minute')
def upload_image(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ImageResponse:
    data = file.file.read()

    try:
        image = PILImage.open(BytesIO(data))
        image.verify()
        image = PILImage.open(BytesIO(data))
        width, height = image.size
        content_type = f'image/{(image.format or "").lower()}'
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid image file')

    key = f'{current_user.id}/{uuid4()}'
    upload_file(key, data, content_type)

    new_image = Image(
        owner_id=current_user.id,
        s3_key=key,
        original_filename=file.filename or 'unnamed',
        content_type=content_type,
        width=width,
        height=height,
        size_bytes=len(data),
        parent_image_id=None
    )
    db.add(new_image)
    db.commit()
    db.refresh(new_image)
    return ImageResponse.model_validate(new_image)

@router.post('/{image_id}/transform', response_model=TransformJobResponse, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit('10/minute')
def transform_image(
    request: Request,
    image_id: int,
    payload: TransformRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TransformJobResponse:
    source = db.query(Image).filter(Image.id == image_id).first()
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Image not found')
    if source.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Not your image')

    cache_key = make_cache_key(image_id, payload.model_dump(exclude_none=True))
    cached = get_cached(cache_key)
    if cached is not None:
        return TransformJobResponse(task_id='cached', status='done', image=ImageResponse.model_validate(cached))

    task = transform_image_task.delay(image_id, payload.model_dump(exclude_none=True), current_user.id, cache_key)
    return TransformJobResponse(task_id=task.id, status='queued')

@router.get('/transform-status/{task_id}', response_model=TransformJobResponse)
def get_transform_status(task_id: str, db: Session = Depends(get_db)) -> TransformJobResponse:
    result = celery_app.AsyncResult(task_id)

    if not result.ready():
        return TransformJobResponse(task_id=task_id, status='pending')

    if not result.successful():
        return TransformJobResponse(task_id=task_id, status='failed', error=str(result.result))

    new_image_id = result.get()
    new_image = db.query(Image).filter(Image.id == new_image_id).first()
    return TransformJobResponse(task_id=task_id, status='done', image=ImageResponse.model_validate(new_image))

@router.get('/{image_id}', response_model=ImageResponse)
@limiter.limit('50/minute')
def get_image(
    request: Request,
    image_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ImageResponse:
    image = db.query(Image).filter(Image.id == image_id).first()
    if image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Image not found')
    if image.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Not your image')
    return ImageResponse.model_validate(image)

@router.get('', response_model=ImageListResponse)
@limiter.limit('50/minute')
def list_images(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ImageListResponse:
    query = db.query(Image).filter(Image.owner_id == current_user.id)
    total = query.count()
    images = (
        query.order_by(Image.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    items = [ImageResponse.model_validate(image) for image in images]
    return ImageListResponse(total=total, page=page, limit=limit, items=items)

@router.delete('/{image_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_image(
    image_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    image = db.query(Image).filter(Image.id == image_id).first()
    if image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Image not found')
    if image.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Not your image')

    ids_to_delete = [image_id]
    frontier = [image_id]
    while frontier:
        children = db.query(Image.id).filter(Image.parent_image_id.in_(frontier)).all()
        child_ids = [child.id for child in children]
        ids_to_delete.extend(child_ids)
        frontier = child_ids

    keys = [row.s3_key for row in db.query(Image.s3_key).filter(Image.id.in_(ids_to_delete)).all()]
    for key in keys:
        delete_file(key)

    db.query(Image).filter(Image.id == image_id).delete()
    db.commit()