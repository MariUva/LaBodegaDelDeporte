import sys
import pytest
from pathlib import Path

# Agrega el directorio raíz del proyecto al PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

from app import create_app

@pytest.fixture
def client():
    app = create_app()  # Crea la app usando la fábrica
    with app.test_client() as client:
        yield client
