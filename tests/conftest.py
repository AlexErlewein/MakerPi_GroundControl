"""Shared pytest fixtures for GroundControl tests"""

import os
import pytest

# Set env vars BEFORE importing app modules that read them at import time
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("EASYVEREIN_REGISTRATION_MOCK", "true")
os.environ.setdefault("EASYVEREIN_API_KEY", "")

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.middleware.sessions import SessionMiddleware

from backend.members.db import get_db
from backend.members.models import Base as MembersBase


@pytest.fixture(scope="function")
def members_db():
    """Per-test in-memory SQLite for members.db"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    MembersBase.metadata.create_all(engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture(scope="function")
def client(members_db):
    """TestClient with overridden member DB and MQTT/scheduler disabled.

    Builds a minimal FastAPI app with only the members router so that
    MQTT and APScheduler from main.py are never started.
    """
    from backend.members.routes import router as members_router

    app = FastAPI()
    app.add_middleware(SessionMiddleware, secret_key="test-secret")
    app.include_router(members_router)

    def override_get_db():
        try:
            yield members_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
