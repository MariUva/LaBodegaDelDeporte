# tests/conftest.py
import pytest
from app import create_app  # Importa la función create_app

@pytest.fixture
def client():
    app = create_app()  # Crea la app usando la fábrica
    with app.test_client() as client:
        yield client
