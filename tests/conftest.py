import os

os.environ.setdefault("API_TOKEN", "test-token")
os.environ.setdefault("UI_PASSWORD", "test-pass")

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)
