import sys
import pytest
from pathlib import Path
from app import create_app, db  # Asegúrate de que 'db' esté importado desde la app

# Agrega el directorio raíz del proyecto al PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

@pytest.fixture
def client():
    app = create_app()  # Crea la app usando la fábrica
    # Antes de las pruebas, asegúrate de crear las tablas
    with app.app_context():
        db.create_all()  # Crea todas las tablas en la base de datos
    with app.test_client() as client:
        yield client
    # Después de las pruebas, puedes eliminar las tablas si lo deseas
    with app.app_context():
        db.drop_all()  # Elimina todas las tablas
