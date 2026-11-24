import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

import pytest

from app import models  # noqa: F401
from app.db import Base, engine


@pytest.fixture(autouse=True, scope="session")
def database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)
