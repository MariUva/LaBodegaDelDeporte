from flask import Blueprint, jsonify
from app import db
from app.models import Producto

bp = Blueprint("main", __name__)

@bp.route("/")
def home():
    return "¡La base de datos está conectada!"

@bp.route("/productos")
def obtener_productos():
    productos = Producto.query.all()
    return jsonify([{"id": p.id, "nombre": p.nombre, "precio": p.precio} for p in productos])
