from app import create_app
import os

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))  # Usa el puerto de Railway o 8000 por defecto
    app.run(host="0.0.0.0", port=port, debug=False)