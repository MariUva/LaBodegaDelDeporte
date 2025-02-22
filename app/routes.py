from flask import Flask
from app import db
from flask import jsonify
from app.models import Producto

# Ruta de prueba
def init_routes(app):
    @app.route("/")
    def home():
        return "¡La base de datos está conectada!"

    @app.route("/productos")
    def obtener_productos():
        productos = Producto.query.all()
        return jsonify([{"id": p.id, "nombre": p.nombre, "precio": p.precio} for p in productos])
