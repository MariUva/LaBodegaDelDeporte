from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config

db = SQLAlchemy()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    app.config['ENV'] = 'production'
    app.config['DEBUG'] = False


    db.init_app(app)
    migrate.init_app(app, db)

    from app.routes import bp  # Importar rutas
    app.register_blueprint(bp)  # Registrar rutas con Blueprint

    return app
