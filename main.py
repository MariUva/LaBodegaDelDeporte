import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config

# Configuración de la aplicación
app = Flask(__name__, template_folder="app/templates", static_folder="app/static")
app.config.from_object(Config)
app.secret_key = "tu_clave_secreta"

# Inicializar la base de datos
db = SQLAlchemy(app)

# ========================== MODELOS ==========================

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    precio = db.Column(db.Float, nullable=False)

# ========================== RUTAS ==========================

@app.route("/")
def home():
    try:
        productos = Producto.query.limit(2).all()  # Obtener 2 productos de la base de datos
    except Exception as e:
        flash(f"Error al obtener productos: {e}", "danger")
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


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = Usuario.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash('Inicio de sesión exitoso', 'success')
            return redirect(url_for('home'))
        
        flash('Correo o contraseña incorrectos', 'danger')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash("Has cerrado sesión", "info")
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if Usuario.query.filter_by(email=email).first():
            flash('El correo ya está registrado', 'warning')
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(password)

        new_user = Usuario(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash('Registro exitoso. Ahora puedes iniciar sesión.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')







# ========================== EJECUCIÓN ==========================
if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    app.run(host="0.0.0.0", port=8000, debug=debug_mode)
