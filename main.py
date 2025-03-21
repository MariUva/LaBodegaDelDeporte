import os
import re
import random
import paypalrestsdk
from flask import Flask, json, render_template, request, redirect, url_for, session, flash, jsonify
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
    descripcion = db.Column(db.Text)
    precio = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    imagen = db.Column(db.String(255))
    categoria_id = db.Column(db.Integer, db.ForeignKey('categoria.id'), nullable=False)  # Nueva columna
    marca_id = db.Column(db.Integer, db.ForeignKey('marca.id'), nullable=False)          # Nueva columna

    # Relaciones
    categoria = db.relationship('Categoria', backref=db.backref('productos', lazy=True))
    marca = db.relationship('Marca', backref=db.backref('productos', lazy=True))

# Tabla intermedia para la relación muchos a muchos entre Categoria y Marca
categoria_marca = db.Table('categoria_marca',
    db.Column('categoria_id', db.Integer, db.ForeignKey('categoria.id'), primary_key=True),
    db.Column('marca_id', db.Integer, db.ForeignKey('marca.id'), primary_key=True)
)

class Categoria(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True)
    marcas = db.relationship('Marca', secondary=categoria_marca, backref=db.backref('categorias', lazy=True))

class Marca(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)


# ========================== RUTAS ==========================

# Ruta principal de la aplicación que obtiene y muestra hasta 2 productos desde la base de datos en la página de inicio.
@app.route("/")
def home():
    try:
        productos = Producto.query.limit(2).all()  # Obtener 2 productos de la base de datos
    except Exception as e:
        flash(f"Error al obtener productos: {e}", "danger")
        productos = []
    return render_template("index.html", productos=productos)

# Ruta para gestionar y mostrar las categorías con sus marcas, asegurando que el usuario esté autenticado antes de acceder.
@app.route("/categorias")
def categorias():
    print("📌 Entrando a /categorias")  

    if 'usuario_id' not in session:  
        print("⚠️ Usuario no autenticado")
        flash("Debes iniciar sesión para acceder a esta página", "warning")
        return redirect(url_for('login'))

    db_session = db.session  
    usuario = db_session.get(Usuario, session['usuario_id'])  

    if not usuario:
        print("⚠️ Usuario no encontrado en la base de datos")
        flash("Usuario no encontrado", "danger")
        return redirect(url_for('login'))

    # 🔹 Obtener todas las categorías con sus marcas
    categorias = db_session.query(Categoria).options(db.joinedload(Categoria.marcas)).all()

    if not categorias:
        print("⚠️ No se encontraron categorías en la base de datos")

    # Convertimos la consulta en un diccionario { "Categoria1": ["Marca1", "Marca2"], ... }
    categorias_dict = {categoria.nombre: [marca.nombre for marca in categoria.marcas] for categoria in categorias}

    return render_template("categorias.html", nombre=usuario.nombre, categorias=categorias_dict)

# Ruta que muestra la página de categorías de deportes con una selección aleatoria de 3 productos.
@app.route("/categorias/deportes")
def categorias_deportes():
    productos = Producto.query.order_by(db.func.random()).limit(3).all()  # Seleccionar 3 productos aleatorios
    return render_template("categorias_deportes.html", productos=productos)

# Ruta para el inicio de sesión que verifica las credenciales del usuario, 
# maneja intentos fallidos y envía un código de verificación si el usuario es administrador.
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'intentos_fallidos' not in session:
        session['intentos_fallidos'] = 0

    if request.method == 'POST':
        correo = request.form.get('correo')
        contraseña = request.form.get('contraseña')

        user = Usuario.query.filter_by(correo=correo).first()

        if user and check_password_hash(user.contraseña, contraseña):
            # Reiniciar intentos fallidos al iniciar sesión correctamente
            session.permanent = True
            session['intentos_fallidos'] = 0
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

                return redirect(url_for('verify'))  # Redirigir a la verificación

            else:
                flash('Inicio de sesión exitoso', 'success')
                print("Sesión antes de redirigir:", session)
                return redirect(url_for('categorias'))

        # Si la autenticación falla, incrementar el contador de intentos
        session['intentos_fallidos'] += 1

        if session['intentos_fallidos'] >= 3:
            flash("Has alcanzado el límite de intentos fallidos. Restablece tu contraseña.", "warning")
            return redirect(url_for('reset_password'))  # Redirigir a la página de recuperación de contraseña
        else:
            flash(f'Correo o contraseña incorrectos. Intento {session["intentos_fallidos"]}/3', 'danger')

    return render_template('login.html')

# Función para validar que una contraseña cumpla con los requisitos de seguridad: 
# mínimo 8 caracteres, al menos una mayúscula, un número y un carácter especial.
def validar_contraseña(password):
    """Verifica que la contraseña tenga al menos 8 caracteres, una mayúscula, un número y un carácter especial."""
    return bool(re.match(r"^(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$", password))

# Ruta para el registro de nuevos usuarios, validando la contraseña, evitando duplicados 
# y almacenando la contraseña encriptada en la base de datos.
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


# Ruta para la verificación en dos pasos, donde el usuario ingresa un código enviado a su correo 
# para completar el inicio de sesión, asegurando el acceso solo a usuarios autenticados.
@app.route('/verify', methods=['GET', 'POST'])
def verify():
    if 'correo' not in session or 'codigo_verificacion' not in session:
        flash("Acceso no autorizado", "danger")
        return redirect(url_for('login'))

    if request.method == 'POST':
        codigo_ingresado = request.form.get('code')
        codigo_verificacion = session.get('codigo_verificacion')

        if codigo_ingresado == codigo_verificacion:
            user = Usuario.query.filter_by(correo=session.get('correo')).first()
            if user:
                session['id'] = user.id
                session.pop('codigo_verificacion', None)
                session.pop('correo', None)
                flash('Verificación exitosa', 'success')

                # Redirigir según el rol del usuario
                if user.es_admin:
                    return redirect(url_for('categorias_admin'))  # Ruta corregida
                else:
                    return redirect(url_for('categorias'))

        flash('Código de verificación incorrecto', 'danger')

    return render_template('verify.html')

# Ruta de administración de categorías, accesible solo para usuarios con privilegios de administrador.
@app.route('/categorias_admin')
def categorias_admin():
    if 'id' not in session or not Usuario.query.get(session['id']).es_admin:
        flash("Acceso no autorizado", "danger")
        return redirect(url_for('login'))
    return render_template('categorias_admin.html')

# Ruta para mostrar el perfil del usuario autenticado, asegurando que esté registrado en la sesión.
@app.route('/perfil')
def perfil():
    if 'usuario_id' not in session:  
        flash("Debes iniciar sesión para acceder a esta página", "warning")
        return redirect(url_for('login'))

    # Obtener el usuario actual desde la base de datos
    usuario = Usuario.query.get(session['usuario_id'])  
    if not usuario:
        flash("Usuario no encontrado", "danger")
        return redirect(url_for('login'))

    # Pasar el usuario a la plantilla
    return render_template('perfil.html', usuario=usuario)

# Ruta para cerrar sesión, limpiando la sesión del usuario y redirigiéndolo a la página de inicio.
@app.route('/logout')
def logout():
    session.clear()
    flash("Has cerrado sesión", "info")
    return redirect(url_for('home'))

from flask import request, jsonify

# Ruta para cambiar la contraseña del usuario autenticado, validando los requisitos de seguridad 
# y actualizándola en la base de datos.
@app.route('/cambiar_contraseña', methods=['POST'])
def cambiar_contraseña():

    print("Contenido de la sesión:", session)  # Verifica si llega aquí

    if 'usuario_id' not in session:
        return jsonify({"error": "Debes iniciar sesión para acceder a esta página"}), 401

    data = request.get_json()
    print(f"Datos recibidos: {data}")  # Verifica si llegan los datos

    nueva_contraseña = data.get('nueva_contraseña')
    if not nueva_contraseña:
        print("Error: No se envió la contraseña")
        return jsonify({"error": "La nueva contraseña es requerida"}), 400

    if not validar_contraseña(nueva_contraseña):
        print("Error: Contraseña no cumple con los requisitos")
        return jsonify({"error": "La contraseña debe tener al menos 8 caracteres, una mayúscula, un número y un carácter especial."}), 400

    usuario = Usuario.query.get(session['usuario_id'])
    if not usuario:
        print("Error: Usuario no encontrado en la BD")
        return jsonify({"error": "Usuario no encontrado"}), 404

    usuario.contraseña = generate_password_hash(nueva_contraseña)
    db.session.commit()
    print("Contraseña actualizada exitosamente")
    
    return jsonify({"message": "Contraseña actualizada correctamente"}), 200

def validar_contraseña(password):
    """Verifica que la contraseña tenga al menos 8 caracteres, una mayúscula, un número y un carácter especial."""
    return bool(re.match(r"^(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$", password))

# Ruta para recuperar la contraseña mediante un código de verificación enviado al correo del usuario.
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

# Ruta para restablecer la contraseña de un usuario que ha solicitado recuperación, 
# validando seguridad y confirmación antes de actualizarla en la base de datos.
@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if 'reset_email' not in session:
        flash("No tienes acceso a esta página", "danger")
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        nueva_contraseña = request.form.get('nueva_contraseña')
        confirmar_contraseña = request.form.get('confirmar_contraseña')

        # Verificar que las contraseñas coincidan
        if nueva_contraseña != confirmar_contraseña:
            flash("Las contraseñas no coinciden", "danger")
            return redirect(url_for('reset_password'))

        # Validar requisitos de seguridad de la contraseña
        if not validar_contraseña(nueva_contraseña):
            flash("La contraseña debe tener al menos 8 caracteres, una mayúscula, una minúscula, un número y un carácter especial.", "danger")
            return redirect(url_for('reset_password'))

        usuario = Usuario.query.filter_by(correo=session['reset_email']).first()

        if usuario:
            usuario.contraseña = generate_password_hash(nueva_contraseña)
            db.session.commit()
            session.pop('reset_email', None)
            flash("Contraseña cambiada con éxito", "success")
            return redirect(url_for('login'))

    return render_template('reset_password.html')

# ========================== CATEGORIAS ADMIN==========================

# Ruta para visualizar la lista de todos los usuarios registrados en la base de datos.
@app.route('/ver_usuarios')
def ver_usuarios():
    usuarios = Usuario.query.all()
    return render_template('ver_usuarios.html', usuarios=usuarios)

@app.route('/crear_producto', methods=['POST'])
def crear_producto():
    nombre = request.form.get('nombre')
    precio = request.form.get('precio')
    categoria = request.form.get('categoria')
    stock = request.form.get('stock')

    nuevo_producto = Producto(nombre=nombre, precio=precio, categoria=categoria, stock=stock)
    db.session.add(nuevo_producto)
    db.session.commit()
    
    flash('Producto creado con éxito', 'success')
    return redirect(url_for('categorias_admin'))

@app.route('/get_marcas')
def get_marcas():
    categoria = request.args.get('categoria')  # Obtener la categoría desde la URL

    # Obtener las marcas asociadas a la categoría desde la base de datos
    categoria_obj = Categoria.query.filter_by(nombre=categoria).first()
    if categoria_obj:
        marcas = [marca.nombre for marca in categoria_obj.marcas]
    else:
        marcas = []

    return jsonify({"marcas": marcas})  # Devolver las marcas en formato JSON

@app.route('/filtrar_productos')
def filtrar_productos():
    categoria_nombre = request.args.get('categoria')
    marca_nombre = request.args.get('marca')

    # Obtener la categoría y marca por su nombre
    categoria = Categoria.query.filter_by(nombre=categoria_nombre).first()
    marca = Marca.query.filter_by(nombre=marca_nombre).first()

    # Consulta inicial con join explícito
    query = Producto.query.join(Categoria).join(Marca)

    if categoria:
        query = query.filter(Producto.categoria_id == categoria.id)
    if marca:
        query = query.filter(Producto.marca_id == marca.id)

    productos = query.all()

    # Verificar qué se obtiene en la base de datos
    for producto in productos:
        print(f"Producto: {producto.nombre}, Categoría: {producto.categoria.nombre if producto.categoria else 'None'}, Marca: {producto.marca.nombre if producto.marca else 'None'}")

    # Convertir los productos a JSON
    productos_json = [{
        "id": producto.id,
        "nombre": producto.nombre,
        "precio": producto.precio,
        "categoria": producto.categoria.nombre if producto.categoria else "Sin categoría",
        "marca": producto.marca.nombre if producto.marca else "Sin marca"
    } for producto in productos]

    return jsonify({"productos": productos_json})

@app.route('/carrito')
def ver_carrito():
    print("Contenido del carrito:", session.get('carrito', []))  # DEBUG
    return render_template('carrito.html', carrito=session.get('carrito', []))


@app.route('/agregar_al_carrito', methods=['POST'])
def agregar_al_carrito():
    producto_id = request.form.get('producto_id')
    
    if 'carrito' not in session:
        session['carrito'] = []  # Inicializar el carrito si no existe
    
    session['carrito'].append(producto_id)  # Agregar producto al carrito
    session.modified = True  # Asegurar que se guarde la sesión
    
    return redirect(url_for('ver_carrito'))

paypalrestsdk.configure({
    "mode": os.getenv("PAYPAL_MODE", "sandbox"),  # "sandbox" o "live"
    "client_id": os.getenv("PAYPAL_CLIENT_ID"),
    "client_secret": os.getenv("PAYPAL_SECRET")
})


@app.route("/pay", methods=["POST"])
def create_payment():
    payment = paypalrestsdk.Payment({
        "intent": "sale",
        "payer": {"payment_method": "paypal"},
        "redirect_urls": {
            "return_url": "http://localhost:5000/payment/execute",
            "cancel_url": "http://localhost:5000/payment/cancel"
        },
        "transactions": [{
            "amount": {"total": "10.00", "currency": "USD"},
            "description": "Compra en La Bodega del Deporte"
        }]
    })

    if payment.create():
        return jsonify({"paymentID": payment.id})
    else:
        return jsonify({"error": payment.error}), 400

@app.route("/payment/execute", methods=["POST"])
def execute_payment():
    payment_id = request.json.get("paymentID")
    payer_id = request.json.get("payerID")
    
    payment = paypalrestsdk.Payment.find(payment_id)
    
    if payment.execute({"payer_id": payer_id}):
        return jsonify({"status": "success"})
    else:
        return jsonify({"error": payment.error}), 400


# ========================== EJECUCIÓN ==========================
if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    app.run(host="0.0.0.0", port=8000, debug=debug_mode)
