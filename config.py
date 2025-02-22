import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    uri = os.getenv("DATABASE_URL")
    if uri and uri.startswith("postgres://"):
        uri = uri.replace("postgres://", "postgresql://", 1)  # Reemplazar solo la primera ocurrencia

    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL") 
    SQLALCHEMY_TRACK_MODIFICATIONS = False
