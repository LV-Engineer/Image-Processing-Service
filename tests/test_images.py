import io
from PIL import Image as PILImage

from models.image import Image


def make_test_image() -> io.BytesIO:
    buf = io.BytesIO()
    PILImage.new('RGB', (100, 80), color=(50, 100, 150)).save(buf, 'JPEG')
    buf.seek(0)
    return buf


def auth_headers(client, email: str) -> dict[str, str]:
    client.post('/auth/signup', json={'email': email, 'password': 'Passw0rd!'})
    token = client.post('/auth/login', json={'email': email, 'password': 'Passw0rd!'}).json()['access_token']
    return {'Authorization': f'Bearer {token}'}


def test_upload_image_success(client):
    headers = auth_headers(client, 'up1@example.com')
    resp = client.post('/images', headers=headers, files={'file': ('t.jpg', make_test_image(), 'image/jpeg')})
    assert resp.status_code == 201
    body = resp.json()
    assert body['width'] == 100
    assert body['height'] == 80
    assert body['parent_image_id'] is None


def test_upload_invalid_file(client):
    headers = auth_headers(client, 'up2@example.com')
    resp = client.post('/images', headers=headers, files={'file': ('t.txt', io.BytesIO(b'not an image'), 'text/plain')})
    assert resp.status_code == 400


def test_get_image_success(client):
    headers = auth_headers(client, 'get0@example.com')
    upload = client.post('/images', headers=headers, files={'file': ('t.jpg', make_test_image(), 'image/jpeg')})
    image_id = upload.json()['id']

    resp = client.get(f'/images/{image_id}', headers=headers)
    assert resp.status_code == 200
    assert resp.json()['id'] == image_id


def test_get_image_not_found(client):
    headers = auth_headers(client, 'get1@example.com')
    resp = client.get('/images/99999', headers=headers)
    assert resp.status_code == 404


def test_get_image_forbidden_for_other_user(client):
    owner_headers = auth_headers(client, 'owner@example.com')
    upload = client.post('/images', headers=owner_headers, files={'file': ('t.jpg', make_test_image(), 'image/jpeg')})
    image_id = upload.json()['id']

    other_headers = auth_headers(client, 'other@example.com')
    resp = client.get(f'/images/{image_id}', headers=other_headers)
    assert resp.status_code == 403


def test_list_images_pagination(client):
    headers = auth_headers(client, 'list1@example.com')
    for _ in range(3):
        client.post('/images', headers=headers, files={'file': ('t.jpg', make_test_image(), 'image/jpeg')})

    resp = client.get('/images?page=1&limit=2', headers=headers)
    body = resp.json()
    assert body['total'] == 3
    assert len(body['items']) == 2


def test_transform_image_creates_derived_image(client, db_session):
    headers = auth_headers(client, 'transform1@example.com')
    upload = client.post('/images', headers=headers, files={'file': ('t.jpg', make_test_image(), 'image/jpeg')})
    image_id = upload.json()['id']

    transform = client.post(f'/images/{image_id}/transform', headers=headers, json={'grayscale': True})
    assert transform.status_code == 202

    child = db_session.query(Image).filter(Image.parent_image_id == image_id).first()
    assert child is not None


def test_delete_image_cascades_to_transform(client, db_session):
    headers = auth_headers(client, 'del1@example.com')
    upload = client.post('/images', headers=headers, files={'file': ('t.jpg', make_test_image(), 'image/jpeg')})
    image_id = upload.json()['id']

    client.post(f'/images/{image_id}/transform', headers=headers, json={'grayscale': True})
    child = db_session.query(Image).filter(Image.parent_image_id == image_id).first()
    assert child is not None
    child_id = child.id

    delete_resp = client.delete(f'/images/{image_id}', headers=headers)
    assert delete_resp.status_code == 204

    assert client.get(f'/images/{child_id}', headers=headers).status_code == 404


def test_transform_image_not_found(client):
    headers = auth_headers(client, 'transform404@example.com')
    resp = client.post('/images/99999/transform', headers=headers, json={'grayscale': True})
    assert resp.status_code == 404


def test_transform_image_forbidden_for_other_user(client):
    owner_headers = auth_headers(client, 'transformowner@example.com')
    upload = client.post('/images', headers=owner_headers, files={'file': ('t.jpg', make_test_image(), 'image/jpeg')})
    image_id = upload.json()['id']

    other_headers = auth_headers(client, 'transformother@example.com')
    resp = client.post(f'/images/{image_id}/transform', headers=other_headers, json={'grayscale': True})
    assert resp.status_code == 403


def test_transform_uses_cache_on_repeat_request(client):
    headers = auth_headers(client, 'transformcache@example.com')
    upload = client.post('/images', headers=headers, files={'file': ('t.jpg', make_test_image(), 'image/jpeg')})
    image_id = upload.json()['id']

    first = client.post(f'/images/{image_id}/transform', headers=headers, json={'grayscale': True})
    assert first.json()['status'] == 'queued'

    second = client.post(f'/images/{image_id}/transform', headers=headers, json={'grayscale': True})
    assert second.json()['task_id'] == 'cached'
    assert second.json()['image']['parent_image_id'] == image_id


def test_transform_status_pending_for_unknown_task(client):
    headers = auth_headers(client, 'status1@example.com')
    resp = client.get('/images/transform-status/does-not-exist', headers=headers)
    assert resp.status_code == 200
    assert resp.json()['status'] == 'pending'


def test_transform_status_done(client):
    headers = auth_headers(client, 'status2@example.com')
    upload = client.post('/images', headers=headers, files={'file': ('t.jpg', make_test_image(), 'image/jpeg')})
    image_id = upload.json()['id']

    transform = client.post(f'/images/{image_id}/transform', headers=headers, json={'grayscale': True})
    task_id = transform.json()['task_id']

    resp = client.get(f'/images/transform-status/{task_id}', headers=headers)
    assert resp.json()['status'] == 'done'
    assert resp.json()['image']['parent_image_id'] == image_id


def test_transform_status_failed(client):
    from core.celery_app import celery_app

    headers = auth_headers(client, 'status3@example.com')
    upload = client.post('/images', headers=headers, files={'file': ('t.jpg', make_test_image(), 'image/jpeg')})
    image_id = upload.json()['id']

    celery_app.conf.task_eager_propagates = False
    try:
        transform = client.post(
            f'/images/{image_id}/transform',
            headers=headers,
            json={'crop': {'left': 0, 'top': 50, 'right': 100, 'bottom': 10}},
        )
        task_id = transform.json()['task_id']

        resp = client.get(f'/images/transform-status/{task_id}', headers=headers)
        assert resp.json()['status'] == 'failed'
        assert resp.json()['error'] is not None
    finally:
        celery_app.conf.task_eager_propagates = True


def test_delete_image_not_found(client):
    headers = auth_headers(client, 'del404@example.com')
    resp = client.delete('/images/99999', headers=headers)
    assert resp.status_code == 404


def test_delete_image_forbidden_for_other_user(client):
    owner_headers = auth_headers(client, 'delowner@example.com')
    upload = client.post('/images', headers=owner_headers, files={'file': ('t.jpg', make_test_image(), 'image/jpeg')})
    image_id = upload.json()['id']

    other_headers = auth_headers(client, 'delother@example.com')
    resp = client.delete(f'/images/{image_id}', headers=other_headers)
    assert resp.status_code == 403