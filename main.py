import os
import re
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
    apellidos = db.Column(db.String(50), nullable=False)
    correo = db.Column(db.String(100), unique=True, nullable=False)
    contraseña = db.Column(db.String(255), nullable=False)
    es_admin = db.Column(db.Boolean, default=False)  

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


@app.route("/categorias")
def categorias():
    if 'id' not in session:
        flash("Debes iniciar sesión para acceder a esta página", "warning")
        return redirect(url_for('login'))

    db_session = db.session  # Si estás usando `db` de SQLAlchemy

    # Obtener el usuario actual desde la base de datos
    usuario = db_session.get(Usuario, session['id'])


    if not usuario:
        flash("Usuario no encontrado", "danger")
        return redirect(url_for('login'))

    # Pasar el nombre del usuario a la plantilla
    return render_template("categorias.html", nombre=usuario.nombre)



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

        if user and check_password_hash(user.contraseña, contraseña):
            session['usuario_id'] = user.id
            session['correo'] = user.correo

            if user.es_admin:
                # Generar código de verificación
                codigo_verificacion = str(random.randint(100000, 999999))
                session['codigo_verificacion'] = codigo_verificacion

                # Enviar código al correo con SendGrid
                message = Mail(
                    from_email=app.config['MAIL_DEFAULT_SENDER'],
                    to_emails=user.correo,
                    subject='Código de Verificación',
                    plain_text_content=f'Tu código de verificación es: {codigo_verificacion}'
                )
                try:
                    sg.send(message)
                    flash('Código enviado al correo', 'info')
                except Exception as e:
                    flash('Error al enviar el correo de verificación', 'danger')

                return redirect(url_for('verify'))  # Redirigir directamente a la verificación

            else:
                # Si no es administrador, iniciar sesión normal
                session['id'] = user.id
                flash('Inicio de sesión exitoso', 'success')
                return redirect(url_for('categorias'))

        flash('Correo o contraseña incorrectos', 'danger')

    return render_template('login.html')


def validar_contraseña(password):
    """Verifica que la contraseña tenga al menos 8 caracteres, una mayúscula, un número y un carácter especial."""
    return bool(re.match(r"^(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$", password))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        apellidos = request.form.get('apellidos')
        correo = request.form.get('correo')
        contraseña = request.form.get('contraseña')

        # Validación de contraseña
        if not validar_contraseña(contraseña):
            flash("La contraseña debe tener al menos 8 caracteres, una mayúscula, un número y un carácter especial.", "danger")
            return redirect(url_for('register'))

        # Verificar si el correo ya está registrado
        if Usuario.query.filter_by(correo=correo).first():
            flash('El correo ya está registrado.', 'warning')
            return redirect(url_for('register'))
        
        # Encriptar la contraseña antes de guardarla
        hashed_contraseña = generate_password_hash(contraseña)

        # Crear nuevo usuario y guardarlo en la base de datos
        new_user = Usuario(nombre=nombre, apellidos=apellidos, correo=correo, contraseña=hashed_contraseña)
        db.session.add(new_user)
        db.session.commit()

        flash('Registro exitoso. Ahora puedes iniciar sesión.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')



@app.route('/verify', methods=['GET', 'POST'])
def verify():
    if 'correo' not in session or 'codigo_verificacion' not in session:
        flash("Acceso no autorizado", "danger")
        return redirect(url_for('login'))

    if request.method == 'POST':
        codigo_ingresado = request.form.get('code')
        codigo_verificacion = session.get('codigo_verificacion')

        if codigo_ingresado == codigo_verificacion:
            session['id'] = Usuario.query.filter_by(correo=session.get('correo')).first().id
            session.pop('codigo_verificacion', None)
            session.pop('correo', None)
            flash('Verificación exitosa', 'success')
            return redirect(url_for('categorias'))
        else:
            flash('Código de verificación incorrecto', 'danger')

    return render_template('verify.html')

@app.route('/perfil')
def perfil():
    if 'id' not in session:
        flash("Debes iniciar sesión para acceder a esta página", "warning")
        return redirect(url_for('login'))

    # Obtener el usuario actual desde la base de datos
    usuario = Usuario.query.get(session['id'])
    if not usuario:
        flash("Usuario no encontrado", "danger")
        return redirect(url_for('login'))

    # Pasar el usuario a la plantilla
    return render_template('perfil.html', usuario=usuario)

@app.route('/logout')
def logout():
    session.clear()
    flash("Has cerrado sesión", "info")
    return redirect(url_for('home'))

from flask import request, jsonify

@app.route('/cambiar_contraseña', methods=['POST'])
def cambiar_contraseña():
    if 'id' not in session:
        return jsonify({"error": "Debes iniciar sesión para acceder a esta página"}), 401

    data = request.get_json()
    nueva_contraseña = data.get('nueva_contraseña')

    if not nueva_contraseña:
        return jsonify({"error": "La nueva contraseña es requerida"}), 400

    # Obtener el usuario actual
    usuario = Usuario.query.get(session['id'])
    if not usuario:
        return jsonify({"error": "Usuario no encontrado"}), 404

    # Actualizar la contraseña
    usuario.contraseña = generate_password_hash(nueva_contraseña)
    db.session.commit()

    return jsonify({"message": "Contraseña actualizada correctamente"}), 200



@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    show_verification = False  # Controla la visibilidad del campo de verificación
    correo = ""

    if request.method == 'POST':
        if 'code' in request.form:  # Verificar el código
            codigo_ingresado = request.form.get('code')
            codigo_verificacion = session.get('codigo_verificacion')

            if codigo_ingresado == codigo_verificacion:
                session.pop('codigo_verificacion', None)
                session['reset_email'] = session.get('correo_reset')
                return redirect(url_for('reset_password'))  # Redirigir a la página de cambio de contraseña
            else:
                flash('Código de verificación incorrecto', 'danger')
                show_verification = True  

        else:  # Primer paso: solicitar correo
            correo = request.form.get('correo')
            usuario = Usuario.query.filter_by(correo=correo).first()

            if usuario:
                # Generar código de verificación
                codigo_verificacion = str(random.randint(100000, 999999))
                session['codigo_verificacion'] = codigo_verificacion
                session['correo_reset'] = correo  # Guardar el correo en sesión

                # Enviar el código por correo con SendGrid
                message = Mail(
                    from_email=app.config['MAIL_DEFAULT_SENDER'],
                    to_emails=correo,
                    subject='Código de Recuperación de Contraseña',
                    plain_text_content=f'Tu código de recuperación es: {codigo_verificacion}'
                )
                try:
                    sg.send(message)
                    flash('Código enviado al correo', 'info')
                    show_verification = True  
                except Exception as e:
                    flash('Error al enviar el correo de recuperación', 'danger')
            else:
                flash('El correo ingresado no está registrado', 'danger')

    return render_template('forgot_password.html', show_verification=show_verification, correo=correo)



@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if 'reset_email' not in session:
        flash("No tienes acceso a esta página", "danger")
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        nueva_contraseña = request.form.get('nueva_contraseña')
        confirmar_contraseña = request.form.get('confirmar_contraseña')

        if nueva_contraseña != confirmar_contraseña:
            flash("Las contraseñas no coinciden", "danger")
            return redirect(url_for('reset_password'))

        usuario = Usuario.query.filter_by(correo=session['reset_email']).first()

        if usuario:
            usuario.contraseña = generate_password_hash(nueva_contraseña)
            db.session.commit()
            session.pop('reset_email', None)
            flash("Contraseña cambiada con éxito", "success")
            return redirect(url_for('login'))

    return render_template('reset_password.html')


# ========================== EJECUCIÓN ==========================
if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    app.run(host="0.0.0.0", port=8000, debug=debug_mode)
