from datetime import datetime
from pydantic import BaseModel

class ImageResponse(BaseModel):
    id: int
    original_filename: str
    content_type: str
    width: int
    height: int
    size_bytes: int
    parent_image_id: int | None
    created_at: datetime

    model_config = {'from_attributes': True}

class ImageListResponse(BaseModel):
    total: int
    page: int
    limit: int
    items: list[ImageResponse]

class TransformRequest(BaseModel):
    resize: dict[str, int] | None = None
    crop: dict[str, int] | None = None
    rotate: float | None = None
    flip: bool | None = None
    mirror: bool | None = None
    grayscale: bool | None = None
    sepia: bool | None = None
    format: str | None = None
    quality: int | None = None

class TransformJobResponse(BaseModel):
    task_id: str
    status: str
    image: ImageResponse | None = None
    error: str | None = None