import pytest
from fastapi.testclient import TestClient

from reprise.api import app
from reprise.db import Base, database_session, engine


@pytest.fixture(scope="function", autouse=True)
def session():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with database_session() as session:
        yield session
        session.rollback()
        session.close()


@pytest.fixture
def client():
    return TestClient(app)
