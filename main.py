from flask import Flask, render_template
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
    productos = Producto.query.limit(2).all()  # Obtener 2 productos de la base de datos
    return render_template("index.html", productos=productos)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)

