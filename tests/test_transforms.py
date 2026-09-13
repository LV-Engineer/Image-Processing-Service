import io

from PIL import Image as PILImage

from core.transforms import apply_transforms
from schemas.image import TransformRequest


def make_bytes(mode='RGB', size=(100, 80), color=(50, 100, 150), fmt='PNG') -> bytes:
    buf = io.BytesIO()
    PILImage.new(mode, size, color=color).save(buf, fmt)
    return buf.getvalue()


def test_resize():
    result = apply_transforms(make_bytes(), TransformRequest(resize={'width': 50, 'height': 40}))
    assert result.width == 50
    assert result.height == 40


def test_crop():
    result = apply_transforms(make_bytes(), TransformRequest(crop={'left': 0, 'top': 0, 'right': 50, 'bottom': 40}))
    assert result.width == 50
    assert result.height == 40


def test_rotate_expands_dimensions():
    result = apply_transforms(make_bytes(size=(100, 80)), TransformRequest(rotate=90))
    assert result.width == 80
    assert result.height == 100


def test_flip():
    result = apply_transforms(make_bytes(), TransformRequest(flip=True))
    assert result.width == 100
    assert result.height == 80


def test_mirror():
    result = apply_transforms(make_bytes(), TransformRequest(mirror=True))
    assert result.width == 100
    assert result.height == 80


def test_sepia():
    result = apply_transforms(make_bytes(), TransformRequest(sepia=True))
    assert result.width == 100
    assert result.height == 80


def test_format_conversion_to_jpeg_from_rgba():
    result = apply_transforms(make_bytes(mode='RGBA', fmt='PNG'), TransformRequest(format='JPEG'))
    assert result.content_type == 'image/jpeg'


def test_quality_option_applied_without_error():
    result = apply_transforms(make_bytes(), TransformRequest(format='JPEG', quality=50))
    assert result.content_type == 'image/jpeg'
