from app import create_app
from waitress import serve

"""
Este archivo es el encargado de ejecutar la aplicación, es decir, es el archivo principal de la aplicación.
"""
app = create_app()

if __name__ == "__main__":
    # Usar Waitress si estás en un entorno de producción
    serve(app, host="0.0.0.0", port=8000)
