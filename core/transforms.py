from dataclasses import dataclass
from typing import Callable
from io import BytesIO

from PIL import Image as PILImage

from schemas.image import TransformRequest

@dataclass
class TransformResult:
    data: bytes
    content_type: str
    width: int
    height: int

def apply_transforms(image_bytes: bytes, payload: TransformRequest) -> TransformResult:
    image: PILImage.Image = PILImage.open(BytesIO(image_bytes))
    image.load()

    if payload.crop is not None:
        box = (payload.crop['left'], payload.crop['top'], payload.crop['right'], payload.crop['bottom'])
        image = image.crop(box)

    if payload.resize is not None:
        size = (payload.resize.get('width', image.width), payload.resize.get('height', image.height))
        image = image.resize(size)

    if payload.rotate is not None:
        image = image.rotate(payload.rotate, expand=True)

    if payload.flip:
        image = image.transpose(PILImage.Transpose.FLIP_TOP_BOTTOM)

    if payload.mirror:
        image = image.transpose(PILImage.Transpose.FLIP_LEFT_RIGHT)

    if payload.grayscale:
        image = image.convert('L')

    if payload.sepia:
        image = _apply_sepia(image)

    output_format = (payload.format or image.format or 'PNG').upper()
    if output_format in ('JPEG', 'JPG') and image.mode in ('RGBA', 'P'):
        image = image.convert('RGB')

    buffer = BytesIO()
    save_kwargs = {'quality': payload.quality} if payload.quality is not None else {}
    image.save(buffer, format=output_format, **save_kwargs)

    return TransformResult(
        data=buffer.getvalue(),
        content_type=f'image/{output_format.lower()}',
        width=image.width,
        height=image.height,
    )

def _apply_sepia(image: PILImage.Image) -> PILImage.Image:
    grayscale = image.convert('L')

    def scale(factor: float) -> Callable[[int], int]:
        def channel(pixel: int) -> int:
            return min(255, int(pixel * factor))
        return channel

    return PILImage.merge('RGB', (
        grayscale.point(scale(1.07)),
        grayscale.point(scale(0.74)),
        grayscale.point(scale(0.43)),
    ))