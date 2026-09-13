import os
from dotenv import dotenv_values

env = {**dotenv_values(".env"), **os.environ}

TEST_DATABASE_URL = env.get("TEST_DATABASE_URL")
assert TEST_DATABASE_URL is not None, "TEST_DATABASE_URL not set in .env or environment"

TEST_REDIS_URL = env.get("TEST_REDIS_URL")
assert TEST_REDIS_URL is not None, "TEST_REDIS_URL not set in .env or environment"

os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["REDIS_URL"] = TEST_REDIS_URL

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import pytest
from fastapi.testclient import TestClient

import api.routes.images as images_routes
import core.tasks as tasks_module
from core.cache import redis_client
from core.celery_app import celery_app
from db.base import Base
from db.session import get_db

engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope='session', autouse=True)
def _celery_eager():
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    celery_app.conf.task_store_eager_result = True


@pytest.fixture(scope='session', autouse=True)
def _create_schema():
    Base.metadata.create_all(engine)
    redis_client.flushdb()
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture()
def db_session():
    session = TestingSessionLocal()
    yield session
    session.close()


@pytest.fixture(autouse=True)
def _clean_db():
    yield
    with engine.begin() as conn:
        conn.execute(text('TRUNCATE TABLE images, users RESTART IDENTITY CASCADE'))
    redis_client.flushdb()


@pytest.fixture()
def fake_s3(monkeypatch):
    store: dict[str, bytes] = {}
    upload = lambda key, data, content_type: store.__setitem__(key, data)
    download = lambda key: store[key]
    delete = lambda key: store.pop(key, None)

    monkeypatch.setattr(images_routes, 'upload_file', upload)
    monkeypatch.setattr(images_routes, 'delete_file', delete)
    monkeypatch.setattr(tasks_module, 'download_file', download)
    monkeypatch.setattr(tasks_module, 'upload_file', upload)
    return store


@pytest.fixture()
def client(db_session, fake_s3):
    from app.main import app

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()