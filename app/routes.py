from flask import Blueprint, render_template, jsonify
from app import db
from app.models import Producto

bp = Blueprint("main", __name__)

@bp.route("/")
def home():
    productos = Producto.query.all()  # Consulta los productos en la DB
    return render_template("index.html", productos=productos)  # Envía los productos a la plantilla

@bp.route("/productos")
def obtener_productos():
    productos = Producto.query.all()
    return jsonify([{"id": p.id, "nombre": p.nombre, "precio": p.precio} for p in productos])
