from app import create_app
from waitress import serve
import os

"""
Este archivo es el encargado de ejecutar la aplicación, es decir, es el archivo principal de la aplicación.
"""
app = create_app()

if __name__ == "__main__":
    # Usar Waitress y el puerto dinámico proporcionado por Railway
    port = int(os.getenv("PORT", 8000))  # Usa el puerto de Railway si está disponible
    serve(app, host="0.0.0.0", port=port)  # Usar 0.0.0.0 para que la app sea accesible en todas las interfaces
