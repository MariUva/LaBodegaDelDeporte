import os
from dotenv import load_dotenv

load_dotenv()

# Imprimir la variable de entorno para verificar que se está cargando
print("DATABASE_URL:", os.getenv("DATABASE_URL"))

class Config:
    uri = os.getenv("DATABASE_URL")
    if uri and uri.startswith("postgres://"):
        uri = uri.replace("postgres://", "postgresql://", 1)  # Reemplazar solo la primera ocurrencia

    SQLALCHEMY_DATABASE_URI = uri  # Aquí se usa la variable de entorno
    SQLALCHEMY_TRACK_MODIFICATIONS = False
