import os
import random
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
from flask_mail import Mail, Message
# Configuración de la aplicación
app = Flask(__name__, template_folder="app/templates", static_folder="app/static")
app.config.from_object(Config)
app.secret_key = "tu_clave_secreta"
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# Configuración de SendGrid
sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))

mail = Mail(app)

# Inicializar la base de datos
db = SQLAlchemy(app)

# ========================== MODELOS ==========================

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    #username = db.Column(db.String(50), unique=True, nullable=False)
    nombre = db.Column(db.String(50), nullable=False)
    correo = db.Column(db.String(100), unique=True, nullable=False)
    contraseña = db.Column(db.String(255), nullable=False)

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
        correo = request.form.get('correo')
        contraseña = request.form.get('contraseña')

        user = Usuario.query.filter_by(correo=correo).first()
        #print("usuario encontrado: ", user.correo)
        
        if user and check_password_hash(user.contraseña, contraseña):
            session['id'] = user.id
            session['correo'] = user.correo
            print("Contraseña válida")
            # Generar un código de verificación
            codigo_verificacion = str(random.randint(100000, 999999))
            session['codigo_verificacion'] = codigo_verificacion

           # Enviar el código por correo usando SendGrid
            message = Mail(
                from_email=app.config['MAIL_DEFAULT_SENDER'],  # Remitente
                to_emails=user.correo,  # Destinatario
                subject='Código de Verificación',  # Asunto del correo
                plain_text_content=f'Tu código de verificación es: {codigo_verificacion}'  # Contenido del correo
            )
            try:
                print("intentando enviar correo")
                response = sg.send(message)  # Enviar el correo
                print("Correo enviado:", response.status_code)
                flash('Inicio de sesión exitoso. Revisa tu correo para el código de verificación.', 'success')
                return redirect(url_for('verify'))  # Redirigir a la página de verificación
            except Exception as e:
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
        nombre = request.form.get('nombre')
        correo = request.form.get('correo')
        contraseña = request.form.get('contraseña')
        
        if Usuario.query.filter_by(correo=correo).first():
            flash('El correo ya está registrado', 'warning')
            return redirect(url_for('register'))
        
        hashed_contraseña = generate_password_hash(contraseña)

        new_user = Usuario(nombre=nombre, correo=correo, contraseña=hashed_contraseña)
        db.session.add(new_user)
        db.session.commit()

        flash('Registro exitoso. Ahora puedes iniciar sesión.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/verify', methods=['GET', 'POST'])
def verify():
    if request.method == 'POST':
        codigo_ingresado = request.form.get('code')
        codigo_verificacion = session.get('codigo_verificacion')

        if codigo_ingresado == codigo_verificacion:
            # Código válido, permitir acceso
            session['id'] = Usuario.query.filter_by(correo=session.get('correo')).first().id
            session.pop('codigo_verificacion', None)
            session.pop('correo_usuario', None)
            flash('Verificación exitosa', 'success')
            return redirect(url_for('home'))
        else:
            flash('Código de verificación incorrecto', 'danger')

    return render_template('verify.html')




# ========================== EJECUCIÓN ==========================
if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    app.run(host="0.0.0.0", port=8000, debug=debug_mode)
