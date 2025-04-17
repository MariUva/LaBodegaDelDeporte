import pytest
from app import app  # Ajusta si tu app está en otro archivo

@pytest.fixture
def client():
    with app.test_client() as client:
        yield client
