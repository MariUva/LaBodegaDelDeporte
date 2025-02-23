import os
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from config import Config

# Asegurar que Flask detecte la carpeta "templates"
app = Flask(__name__, template_folder="app/templates", static_folder="app/static")
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
    try:
        productos = Producto.query.limit(2).all()  # Obtener 2 productos de la base de datos
    except Exception as e:
        print(f"Error al obtener productos: {e}")
        productos = []
    return render_template("index.html", productos=productos)


@app.route("/categorias/mujer")
def categorias_mujer():
    return "<h1>Página de categorías y marcas para Mujer</h1>"

@app.route("/categorias/hombre")
def categorias_hombre():
    return "<h1>Página de categorías y marcas para Hombre</h1>"

@app.route("/categorias/deportes")
def categorias_deportes():
    productos = Producto.query.order_by(db.func.random()).limit(3).all()  # Seleccionar 3 productos aleatorios
    return render_template("categorias_deportes.html", productos=productos)

if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    app.run(host="0.0.0.0", port=8000, debug=debug_mode)
