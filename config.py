import os
from dotenv import load_dotenv

# Cargar variables de entorno desde un archivo .env si existe
load_dotenv()

# Imprimir la variable de entorno para verificar que se está cargando correctamente
print("DATABASE_URL:", os.getenv("DATABASE_URL"))

class Config:
    # Configuración de la base de datos
    uri = os.getenv("DATABASE_URL")
    if uri and uri.startswith("postgres://"):
        uri = uri.replace("postgres://", "postgresql://", 1)  # Reemplazo para compatibilidad con SQLAlchemy

    SQLALCHEMY_DATABASE_URI = uri or "sqlite:///database.db"  # Base de datos por defecto en SQLite si no hay PostgreSQL
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Configuración de seguridad
    SECRET_KEY = os.getenv("SECRET_KEY", "SENDGRID_API_KEY")

    # Configuración de correo (SMTP)
    #MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")  # Servidor SMTP (por defecto Gmail)
    #MAIL_PORT = int(os.getenv("MAIL_PORT", 587))  # Puerto SMTP
    #MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() == "true"  # Habilitar TLS
    #MAIL_USE_SSL = os.getenv("MAIL_USE_SSL", "false").lower() == "true"  # Habilitar SSL (opcional)
    #MAIL_USERNAME = os.getenv("MAIL_USERNAME")  # Correo electrónico de envío
    #MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")  # Contraseña o App Password
    #MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", MAIL_USERNAME)  # Remitente por defecto

    # Configuración de SendGrid
    SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "juanm.londonom@uqvirtual.edu.co")

    # Configuración de Cloudinary (para subir imágenes)
    CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
    CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
    CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")
    
    
    # Otras configuraciones opcionales
    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    TESTING = False
    ENV = 'production'