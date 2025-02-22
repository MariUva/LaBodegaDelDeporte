from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

db = SQLAlchemy(app)

# Modelo de prueba
class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    precio = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f"<Producto {self.nombre}>"

# Ruta de prueba
@app.route("/")
def home():
    return "¡La base de datos está conectada!"
