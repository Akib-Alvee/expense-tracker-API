import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app import models  # noqa: F401  (registers tables on Base.metadata)
from app.config import settings
from app.database import Base
from app.deps import get_db
from app.main import app

dev_url = make_url(settings.database_url)
test_url = dev_url.set(database=f"{dev_url.database}_test")


def _ensure_test_database():
    admin = create_engine(dev_url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        exists = conn.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": test_url.database},
        )
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{test_url.database}"'))
    admin.dispose()


@pytest.fixture(scope="session")
def engine():
    # Safety guard: never run destructive test setup against a non-test database
    assert test_url.database.endswith("_test")
    _ensure_test_database()
    engine = create_engine(test_url)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def clean_tables(engine):
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE users, expenses RESTART IDENTITY CASCADE"))


@pytest.fixture
def client(engine):
    TestingSession = sessionmaker(bind=engine, autoflush=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def make_user(client):
    """Sign up + log in a user; returns the Authorization headers."""

    def _make(email="alice@example.com", password="password123"):
        r = client.post("/auth/signup", json={"email": email, "password": password})
        assert r.status_code == 201, r.text
        r = client.post("/auth/login", data={"username": email, "password": password})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    return _make