import os
from flask import Flask, render_template, request, redirect, url_for
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
    return render_template("categoria_mujer.html")

@app.route("/categorias/hombre")
def categorias_hombre():
    return render_template("categoria_hombre.html")

@app.route("/categorias/deportes")
def categorias_deportes():
    productos = Producto.query.order_by(db.func.random()).limit(3).all()  # Seleccionar 3 productos aleatorios
    return render_template("categorias_deportes.html", productos=productos)

@app.route('/login', methods=['GET', 'POST'])  # Acepta GET y POST
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if email == "admin@example.com" and password == "123456":  # Prueba con credenciales fijas
            return redirect(url_for('home'))  # Redirigir al usuario si los datos son correctos
        else:
            error = "Correo o contraseña incorrectos"
            return render_template('login.html', error=error)  # Volver a mostrar el login con un mensaje de error

    return render_template('login.html')  # Si es GET, solo muestra el formulario

if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    app.run(host="0.0.0.0", port=8000, debug=debug_mode)
