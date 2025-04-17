from app import create_app

"""
Este archivo es el encargado de ejecutar la aplicación, es decir, es el archivo principal de la aplicación.
"""
app = create_app()

if __name__ == "__main__":
    app.run(debug=False)
