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
import cloudinary
import cloudinary.uploader
import cloudinary.api
import mercadopago
from flask import request, redirect, url_for, flash

import logging
app.logger.setLevel(logging.DEBUG)  # Capturar detalles más completos


# Configuración de Mercado Pago
#sdk = mercadopago.SDK(os.getenv("MERCADOPAGO_ACCESS_TOKEN"))

sdk = mercadopago.SDK("APP_USR-7356850175082371-050708-0ef8768d3184ead8d91f27da42a86ac0-466327316")
# Configuración de SendGrid
sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))

mail = Mail(app)

# Inicializar la base de datos
db = SQLAlchemy(app)

# Configurar Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)


# ========================== MODELOS ==========================

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    #username = db.Column(db.String(50), unique=True, nullable=False)
    nombre = db.Column(db.String(50), nullable=False)
    apellidos = db.Column(db.String(50), nullable=False)
    correo = db.Column(db.String(100), unique=True, nullable=False)
    contraseña = db.Column(db.String(255), nullable=False)
    es_admin = db.Column(db.Boolean, default=False) 
    es_auxbodega = db.Column(db.Boolean, default=False) 

class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    precio = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    imagen = db.Column(db.String(255))
    categoria_id = db.Column(db.Integer, db.ForeignKey('categoria.id'), nullable=False)  # Nueva columna
    marca_id = db.Column(db.Integer, db.ForeignKey('marca.id'), nullable=False)          # Nueva columna
    lote = db.Column(db.String(50), nullable=False) 
    verificado = db.Column(db.Boolean, default=False)  
    activo = db.Column(db.Boolean, default=True, nullable=False)
    ubicacion_id = db.Column(db.Integer, db.ForeignKey('ubicacion_bodega.id'), nullable=True)
    ubicacion = db.relationship('UbicacionBodega', backref=db.backref('productos', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'precio': float(self.precio) if self.precio is not None else 0.0,
            'stock': self.stock,
            'imagen': self.imagen,
            'categoria': self.categoria.to_dict() if self.categoria else None,
            'categoria_id': self.categoria_id,
            'marca': self.marca.to_dict() if self.marca else None,
            'marca_id': self.marca_id,
            'ubicacion': self.ubicacion.to_dict() if self.ubicacion else None,
            'ubicacion_id': self.ubicacion_id,
            'activo': self.activo  
        }    


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

    def to_dict(self, include_marcas=False):
        data = {
            'id': self.id,
            'nombre': self.nombre
        }
        if include_marcas:
            data['marcas'] = [m.to_dict() for m in self.marcas]
        return data

class Marca(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)

    def to_dict(self, include_categorias=False):
        data = {
            'id': self.id,
            'nombre': self.nombre
        }
        if include_categorias:
            data['categorias'] = [c.to_dict() for c in self.categorias]
        return data

class UbicacionBodega(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categoria.id'), nullable=False, unique=True)
    estante = db.Column(db.String(50), nullable=False)

    categoria = db.relationship('Categoria', backref=db.backref('ubicacion', uselist=False))

    def to_dict(self):
        return {
            'id': self.id,
            'categoria_id': self.categoria_id,
            'categoria': self.categoria.nombre if self.categoria else None,
            'estante': self.estante
        }

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

    # Obtener productos activos
    productos_activos = db_session.query(Producto).filter(Producto.activo == True).all()

    # Obtener todas las categorías con sus marcas
    categorias = db_session.query(Categoria).options(db.joinedload(Categoria.marcas)).all()

    if not categorias:
        print("⚠️ No se encontraron categorías en la base de datos")

    # Convertimos la consulta en un diccionario { "Categoria1": ["Marca1", "Marca2"], ... }
    categorias_dict = {categoria.nombre: [marca.nombre for marca in categoria.marcas] for categoria in categorias}

    return render_template("categorias.html", nombre=usuario.nombre, categorias=categorias_dict, productos=productos_activos)

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
            session.clear()
            # Vaciar el carrito ANTES de iniciar sesión
           
            session['carrito'] = []
            session.modified = True
           
           # Reiniciar intentos fallidos al iniciar sesión correctamente
            session.permanent = False
            session['intentos_fallidos'] = 0
            session['usuario_id'] = user.id
            session['correo'] = user.correo
            session['es_admin'] = user.es_admin
            session['es_auxbodega'] = user.es_auxbodega  # Guardar estado de auxbodega en sesión
            session.modified = True

            # Manejo de redirección según tipo de usuario
            if user.es_admin:
                # Lógica de verificación en dos pasos para admin
                codigo_verificacion = str(random.randint(100000, 999999))
                session['codigo_verificacion'] = codigo_verificacion

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

                return redirect(url_for('verify'))

            elif user.es_auxbodega:
                # Redirigir directamente a ingreso de inventario para auxbodega
                flash('Inicio de sesión exitoso como Auxiliar de Bodega', 'success')
                return redirect(url_for('ingreso_inventario'))

            else:
                # Usuario normal
                flash('Inicio de sesión exitoso', 'success')
                return redirect(url_for('categorias'))

        # Manejo de intentos fallidos
        session['intentos_fallidos'] += 1

        if session['intentos_fallidos'] >= 3:
            flash("Has alcanzado el límite de intentos fallidos. Restablece tu contraseña.", "warning")
            return redirect(url_for('reset_password'))
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

    # Vaciar el carrito al cerrar sesión también
    session.pop('carrito', None)
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
    try:
        # Verificar si el contenido es multipart/form-data
        if 'multipart/form-data' not in request.content_type:
            print("⚠️ Error: El contenido no es multipart/form-data")
            return jsonify({'success': False, 'error': 'El contenido debe ser multipart/form-data'}), 400

        # Depuración: Imprimir los datos recibidos
        print("📥 request.form:", request.form)
        print("📥 request.files:", request.files)

        # Obtener los datos del formulario
        nombre = request.form.get('nombre')
        descripcion = request.form.get('descripcion')
        precio = request.form.get('precio')
        stock = request.form.get('stock')
        categoria_id = request.form.get('categoria_id')
        marca_id = request.form.get('marca_id')
        imagen = request.files.get('imagen')

        # Validar que todos los campos requeridos estén presentes
        if not all([nombre, descripcion, precio, stock, categoria_id, marca_id, imagen]):
            print("❌ Error: Faltan campos obligatorios")
            return jsonify({'success': False, 'error': 'Todos los campos son obligatorios'}), 400

        # Subir la imagen a Cloudinary
        try:
            upload_result = cloudinary.uploader.upload(imagen, folder="productos")
            imagen_url = upload_result.get("secure_url")
            print(f"✅ Imagen subida a Cloudinary: {imagen_url}")
        except Exception as e:
            print(f"❌ Error al subir la imagen a Cloudinary: {str(e)}")
            return jsonify({'success': False, 'error': f'Error al subir la imagen: {str(e)}'}), 500

        # Crear el producto en la base de datos
        nuevo_producto = Producto(
            nombre=nombre,
            descripcion=descripcion,
            precio=float(precio),
            stock=int(stock),
            categoria_id=int(categoria_id),
            marca_id=int(marca_id),
            imagen=imagen_url
        )
        db.session.add(nuevo_producto)
        db.session.commit()

        print("✅ Producto creado con éxito")
        return jsonify({'success': True, 'message': 'Producto creado con éxito'}), 201

    except Exception as e:
        app.logger.error(f"❌ Error al crear el producto: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500
       
@app.route('/editar_producto', methods=['POST'])
def editar_producto():
    try:
        # Verificar si el contenido es multipart/form-data
        if 'multipart/form-data' not in request.content_type:
            return jsonify({'success': False, 'error': 'El contenido debe ser multipart/form-data'}), 400

        # Obtener los datos del formulario
        producto_id = request.form.get('producto_id')
        nombre = request.form.get('nombre')
        descripcion = request.form.get('descripcion')
        precio = request.form.get('precio')
        stock = request.form.get('stock')
        categoria_id = request.form.get('categoria_id')
        marca_id = request.form.get('marca_id')
        imagen = request.files.get('imagen')

        # Obtener el producto existente
        producto = Producto.query.get(producto_id)
        if not producto:
            return jsonify({'success': False, 'error': 'Producto no encontrado'}), 404

        # Actualizar los datos del producto
        producto.nombre = nombre
        producto.descripcion = descripcion
        producto.precio = float(precio)
        producto.stock = int(stock)
        producto.categoria_id = int(categoria_id)
        producto.marca_id = int(marca_id)

        # Si hay una nueva imagen, subirla a Cloudinary
        if imagen:
            try:
                upload_result = cloudinary.uploader.upload(imagen, folder=f"productos/{producto.id}")
                producto.imagen = upload_result.get("secure_url")
            except Exception as e:
                return jsonify({'success': False, 'error': f'Error al subir la imagen: {str(e)}'}), 500

        # Guardar los cambios en la base de datos
        db.session.commit()
        return jsonify({'success': True}), 200

    except Exception as e:
        app.logger.error(f"Error al editar el producto: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500
        
@app.route('/get_productos', methods=['GET'])
def obtener_productos():
    try:
        search_term = request.args.get('search', '').strip()
        categoria_id = request.args.get('categoria_id', type=int)
        marca_id = request.args.get('marca_id', type=int)
        
        # Filtro base para solo productos activos
        query = db.session.query(Producto).filter(Producto.activo == True)
        
        # Filtros adicionales
        if search_term:
            query = query.filter(
                db.or_(
                    Producto.nombre.ilike(f'%{search_term}%'),
                    Producto.descripcion.ilike(f'%{search_term}%'),
                    Producto.marca.has(Marca.nombre.ilike(f'%{search_term}%')),
                    Producto.categoria.has(Categoria.nombre.ilike(f'%{search_term}%'))
                )
            )
        
        if categoria_id:
            query = query.filter_by(categoria_id=categoria_id)
            
        if marca_id:
            query = query.filter_by(marca_id=marca_id)
        
        productos = query.all()
        
        productos_json = [p.to_dict() for p in productos]
        return jsonify(productos_json)
        
    except Exception as e:
        app.logger.error(f"Error al obtener productos: {str(e)}", exc_info=True)
        return jsonify({'error': 'Error interno del servidor'}), 500
        
    except Exception as e:
        app.logger.error(f"Error al obtener productos: {str(e)}", exc_info=True)
        return jsonify({'error': 'Error interno del servidor'}), 500
    
@app.route('/get_categorias', methods=['GET'])
def get_categorias():
    try:
        categorias = Categoria.query.all()
        return jsonify([categoria.to_dict() for categoria in categorias])
    except Exception as e:
        app.logger.error(f"Error al obtener categorías: {str(e)}", exc_info=True)
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/get_marcas_por_categoria', methods=['GET'])
def get_marcas():
    categoria_nombre = request.args.get('categoria')  # Obtener el nombre de la categoría desde los parámetros
    categoria = Categoria.query.filter_by(nombre=categoria_nombre).first()  # Buscar la categoría por nombre

    if categoria:
        marcas = [marca.nombre for marca in categoria.marcas]  # Obtener las marcas asociadas
        return jsonify({"marcas": marcas})
    else:
        return jsonify({"marcas": []})  # Si no se encuentra la categoria
    
@app.route('/get_todas_las_marcas', methods=['GET'])
def get_todas_las_marcas():
    try:
        marcas = Marca.query.all()
        return jsonify([marca.to_dict() for marca in marcas])
    except Exception as e:
        app.logger.error(f"Error al obtener todas las marcas: {str(e)}", exc_info=True)
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/delete_producto/<int:product_id>', methods=['POST'])
def delete_producto(product_id):
    """
    Elimina un producto de la base de datos y, si tiene imagen, también la borra de Cloudinary.
    """
    try:
        producto = Producto.query.get(product_id)
        
        if not producto:
            return jsonify({"success": False, "error": "Producto no encontrado"}), 404

        # Si el producto tiene una imagen, eliminarla de Cloudinary
        if producto.imagen:
            try:
                public_id = producto.imagen.split("/")[-1].split(".")[0]
                cloudinary.uploader.destroy(public_id)
            except Exception as e:
                app.logger.error(f"Error al eliminar imagen de Cloudinary: {str(e)}")

        # Eliminar el producto de la base de datos
        db.session.delete(producto)
        db.session.commit()

        return jsonify({"success": True, "message": "Producto eliminado correctamente"})

    except Exception as e:
        app.logger.error(f"Error al eliminar producto: {str(e)}", exc_info=True)
        return jsonify({"success": False, "error": "Error interno del servidor"}), 500

@app.route('/filtrar_productos')
def filtrar_productos():
    categoria_nombre = request.args.get('categoria')
    marca_nombre = request.args.get('marca')

    # Obtener la categoría y marca por su nombre
    categoria = Categoria.query.filter_by(nombre=categoria_nombre).first()
    marca = Marca.query.filter_by(nombre=marca_nombre).first()

    # Consulta inicial con join explícito y filtro por activo=True
    query = Producto.query.filter(Producto.activo == True).join(Categoria).join(Marca)

    if categoria:
        query = query.filter(Producto.categoria_id == categoria.id)
    if marca:
        query = query.filter(Producto.marca_id == marca.id)

    productos = query.all()

    # Convertir los productos a JSON
    productos_json = [{
        "id": producto.id,
        "nombre": producto.nombre,
        "descripcion": producto.descripcion,
        "precio": producto.precio,
        "stock": producto.stock,
        "imagen": producto.imagen,
        "categoria": producto.categoria.nombre if producto.categoria else "Sin categoría",
        "marca": producto.marca.nombre if producto.marca else "Sin marca",
        "activo": producto.activo
    } for producto in productos]

    return jsonify({"productos": productos_json})

@app.route('/carrito')
def ver_carrito():
    print("Contenido del carrito:", session.get('carrito', []))  # DEBUG
    return render_template('carrito.html', carrito=session.get('carrito', []))


@app.route('/agregar_al_carrito', methods=['POST'])
def agregar_al_carrito():
    producto_id = request.form.get('producto_id')
    nombre = request.form.get('nombre')
    precio = float(request.form.get('precio'))

    if 'carrito' not in session:
        session['carrito'] = []  # Inicializar el carrito si no existe

    # Convertimos la sesión en una lista modificable
    carrito = session['carrito']

    # Buscar si el producto ya está en el carrito
    for producto in carrito:
        if producto['id'] == producto_id:
            producto['cantidad'] += 1
            break
    else:
        carrito.append({
            'id': producto_id,
            'nombre': nombre,
            'precio': precio,
            'cantidad': 1
        })

    session['carrito'] = carrito
    session.modified = True  # Asegurar que se guarde la sesión

    print("Carrito actualizado:", session['carrito'])  # 🛠️ Verifica en la terminal

    return redirect(url_for('ver_carrito'))

@app.route('/actualizar_carrito', methods=['POST'])
def actualizar_carrito():
    try:
        data = request.get_json()
        session['carrito'] = data['carrito']
        session.modified = True
        return jsonify({'success': True})
    except Exception as e:
        app.logger.error(f"Error al actualizar carrito: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

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

@app.route('/limpiar_carrito', methods=['POST'])
def limpiar_carrito():
    try:
        session.pop('carrito', None)
        session.modified = True
        return jsonify({'success': True})
    except Exception as e:
        app.logger.error(f"Error al limpiar carrito: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ========================== PAGO ========================================================

@app.route('/crear_preferencia', methods=['POST'])
def crear_preferencia():
    # Obtener los productos enviados desde el frontend (carrito)
    carrito = request.json.get('items', [])

    # Verificar que el carrito tenga los productos correctos
    print("Carrito recibido:", carrito)  # Agrega este print para depurar

    if not carrito:
        return jsonify({"error": "El carrito está vacío"}), 400

    # Crea la preferencia de pago con los productos del carrito
    preference_data = {
        "items": carrito,
        "back_urls": {
            "success": "https://labodegadeldeporte-production.up.railway.app/exito",
            "failure": "https://labodegadeldeporte-production.up.railway.app/error",
            "pending": "https://labodegadeldeporte-production.up.railway.app/pendiente"
        },
        "auto_return": "approved"
    }

    # Crear la preferencia en Mercado Pago
    preference_response = sdk.preference().create(preference_data)

    # Retornar el enlace de pago (init_point)
    if preference_response["status"] == 201:
        return jsonify({
            "init_point": preference_response["response"]["init_point"]
        })
    else:
        return jsonify({"error": "Error al crear la preferencia de pago"}), 500



@app.route('/procesar_pago', methods=['POST'])
def procesar_pago():
    if 'usuario_id' not in session:
        return jsonify({'success': False, 'error': 'Debes iniciar sesión para pagar'}), 401

    try:
        data = request.get_json()
        carrito = data.get('carrito', [])

        if not carrito:
            return jsonify({'success': False, 'error': 'El carrito está vacío'}), 400

        items = []
        for producto in carrito:
            prod_db = db.session.get(Producto, producto['id'])
            if not prod_db or prod_db.stock < producto['cantidad']:
                return jsonify({
                    'success': False,
                    'error': f'No hay suficiente stock para {prod_db.nombre if prod_db else "un producto"}'
                }), 400

            items.append({
                "title": prod_db.nombre[:127],
                "quantity": int(producto['cantidad']),
                "currency_id": "COP",
                "unit_price": float(prod_db.precio)
            })

        preference_data = {
            "items": items,
            "payer": {
                "name": session.get('nombre', 'Cliente'),
                "email": session.get('correo', '')
            },
            "back_urls": {
                "success": url_for("success", _external=True),
                "failure": url_for("failure", _external=True),
                "pending": url_for("pending", _external=True)
            },
            "auto_return": "approved",
            "notification_url": url_for("mp_webhook", _external=True)
        }

        preference_response = sdk.preference().create(preference_data)
        if preference_response['status'] not in [200, 201]:
            error_msg = preference_response.get('response', {}).get('message', 'Error desconocido')
            return jsonify({'success': False, 'error': f'Error al crear preferencia: {error_msg}'}), 500

        return jsonify({'success': True, 'init_point': preference_response['response']['init_point']})

    except Exception as e:
        app.logger.error(f"Error al procesar el pago: {str(e)}")
        flash("Error al crear la preferencia de pago", "danger")
        return redirect(url_for("categorias"))

    

@app.route('/pago', methods=['GET', 'POST'])
def pago():
    if request.method == 'GET':
        carrito = session.get('carrito', [])
        total = sum(p['precio'] * p['cantidad'] for p in carrito)

        preference_data = {
            "items": [
                {
                    "title": p["nombre"],
                    "quantity": p["cantidad"],
                    "unit_price": float(p["precio"]),
                    "currency_id": "COP"
                } for p in carrito
            ],
            "back_urls": {
                "success": url_for('exito_pago', _external=True),
                "failure": url_for('fallo_pago', _external=True),
                "pending": url_for('pendiente_pago', _external=True)
            },
            "auto_return": "approved"
        }

        preference_response = sdk.preference().create(preference_data)
        init_point = preference_response["response"]["init_point"]

        return render_template('pago.html', carrito=carrito, total=total, init_point=init_point)

    elif request.method == 'POST':
        try:
            data = request.get_json()
            carrito = data.get('carrito', [])
            for producto_carrito in carrito:
                producto = Producto.query.get(producto_carrito['id'])
                if producto.stock < producto_carrito['cantidad']:
                    return jsonify({'success': False, 'error': f'Sin stock: {producto.nombre}'}), 400
                producto.stock -= producto_carrito['cantidad']
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error al procesar pago: {str(e)}")
            return jsonify({'success': False, 'error': 'Error interno al procesar el pago'}), 500


@app.route('/pago_exitoso')
def pago_exitoso():
    carrito = session.get('carrito', [])
    for item in carrito:
        producto = db.session.get(Producto, item['id'])
        if producto:
            producto.stock -= item['cantidad']
    db.session.commit()
    session.pop('carrito', None)
    flash("¡Pago exitoso! Gracias por tu compra.", "success")
    return redirect(url_for('categorias'))

@app.route('/pago_fallido')
def pago_fallido():
    flash("El pago fue rechazado o falló. Por favor, intenta nuevamente.", "danger")
    return redirect(url_for('ver_carrito'))

@app.route('/pago_pendiente')
def pago_pendiente():
    flash("Tu pago está pendiente. Te notificaremos cuando se confirme.", "info")
    return redirect(url_for('categorias'))



@app.route("/success")
def success():
    return render_template("pago_resultado.html", estado="exitoso", mensaje="✅ El pago fue realizado con éxito. ¡Gracias por tu compra!")

@app.route("/failure")
def failure():
    return render_template("pago_resultado.html", estado="fallido", mensaje="❌ El pago no fue exitoso. Por favor, intenta de nuevo.")

@app.route("/pending")
def pending():
    return render_template("pago_resultado.html", estado="pendiente", mensaje="⏳ El pago está pendiente. Te notificaremos cuando se confirme.")


# Endpoint para pagar un solo producto
@app.route("/pagar/<int:producto_id>")
def pagar(producto_id):
    app.logger.info(f"Iniciando pago para el producto con ID: {producto_id}")
    producto = obtener_producto_por_id(producto_id)

    if not producto:
        flash("Producto no encontrado", "warning")
        return redirect(url_for("categorias"))

    preference_data = {
        "items": [{
            "title": producto["nombre"],
            "quantity": 1,
            "currency_id": "COP",
            "unit_price": float(producto["precio"])
        }],
        "back_urls": {
            "success": url_for("pago_exitoso", _external=True),
            "failure": url_for("pago_fallido", _external=True),
            "pending": url_for("pago_pendiente", _external=True)
        },
        "auto_return": "approved",
        "notification_url": url_for("mp_webhook", _external=True)
    }

    try:
        preference_response = sdk.preference().create(preference_data)
        return redirect(preference_response["response"]["init_point"])
    except Exception as e:
        app.logger.error(f"Error al crear la preferencia: {str(e)}")
        flash("Error al crear la preferencia de pago", "danger")
        return redirect(url_for("categorias"))


@app.route('/pagar_carrito')
def pagar_carrito():
    if 'usuario_id' not in session:
        flash("Debes iniciar sesión para pagar", "warning")
        return redirect(url_for('login'))

    carrito = session.get('carrito', [])
    if not carrito:
        flash("El carrito está vacío", "warning")
        return redirect(url_for('categorias'))

    try:
        items = []
        for producto in carrito:
            prod_db = db.session.get(Producto, producto['id'])
            if not prod_db or prod_db.stock < producto['cantidad']:
                flash(f"No hay suficiente stock para {prod_db.nombre if prod_db else 'un producto'}", "danger")
                return redirect(url_for('ver_carrito'))

            items.append({
                "title": prod_db.nombre[:127],
                "quantity": int(producto['cantidad']),
                "currency_id": "COP",
                "unit_price": float(prod_db.precio)
            })

        preference_data = {
            "items": items,
            "back_urls": {
                "success": url_for("pago_exitoso", _external=True),
                "failure": url_for("pago_fallido", _external=True),
                "pending": url_for("pago_pendiente", _external=True)
            },
            "auto_return": "approved"
        }

        preference_response = sdk.preference().create(preference_data)
        return redirect(preference_response["response"]["init_point"])
        
    except Exception as e:
        app.logger.error(f"Error en pagar_carrito: {str(e)}")
        flash("Error al procesar el pago", "danger")
        return redirect(url_for('ver_carrito'))

@app.route('/mp_webhook', methods=['POST'])
def mp_webhook():
    try:
        data = request.get_json()
        app.logger.info(f"📩 Webhook recibido: {data}")

        if data.get('action') == 'payment.updated':
            payment_id = data['data']['id']
            payment_info = sdk.payment().get(payment_id)

            if payment_info['status'] in [200, 201]:
                status = payment_info['response'].get('status')
                app.logger.info(f"Estado del pago {payment_id}: {status}")

                if status == 'approved':
                    # Aquí puedes actualizar la base de datos, enviar correos, etc.
                    app.logger.info("✅ Pago aprobado. Se podría vaciar el carrito o marcar pedido como pagado.")
                    # OJO: No uses `session.pop` aquí directamente. Los webhooks no tienen sesión de usuario.
            else:
                app.logger.error(f"❌ Error al consultar el pago {payment_id}: {payment_info}")

        return jsonify({'status': 'success'}), 200

    except Exception as e:
        app.logger.error(f"❌ Error en webhook: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500



# ========================== FIN PAGO ========================================================


# Función para obtener el carrito del usuario
def obtener_carrito_usuario():
    carrito = session.get('carrito', [])
    productos = []
    
    for item in carrito:
        producto = Producto.query.get(item['id'])
        if producto:
            producto_dict = producto.to_dict()
            producto_dict['cantidad'] = item['cantidad']
            productos.append(producto_dict)
    
    return productos

def obtener_producto_por_id(producto_id):
    # Usar session.get() en lugar de Query.get()
    producto = db.session.get(Producto, producto_id)
    if producto:
        return {
            'id': producto.id,
            'nombre': producto.nombre,
            'precio': float(producto.precio)
        }
    return None





# Ruta de inicio
@app.route('/')
def index():
    if 'usuario_id' in session:
        usuario = Usuario.query.get(session['usuario_id'])
        if usuario.es_auxbodega:
            return redirect(url_for('ingreso_inventario'))
    return "Bienvenido a la tienda"



@app.route('/admin_inventario')
def inventario():
    if 'usuario_id' not in session or (not session.get('es_admin') and not session.get('es_auxbodega')):
        flash("Acceso no autorizado", "danger")
        return redirect(url_for('login'))
    
    # Obtener todos los productos sin filtrar por activo
    productos = Producto.query.all()
    return render_template('admin_inventario.html', productos=productos)

@app.route('/ingreso-inventario', methods=['GET', 'POST'])
def ingreso_inventario():
    # Verificar autenticación y rol
    if 'usuario_id' not in session or not session.get('es_auxbodega'):
        flash("Acceso no autorizado", "danger")
        return redirect(url_for('login'))

    if request.method == 'GET':
        marcas = Marca.query.all()
        categorias = Categoria.query.all()  # Asegúrate de incluir las categorías
        ubicaciones = db.session.query(UbicacionBodega).all()  # Recupera las ubicaciones desde la base de datos
        return render_template('ingresoInventario.html', marcas=marcas, categorias=categorias, ubicaciones=ubicaciones)

    # Si es POST
    try:
        app.logger.info("Headers: %s", request.headers)
        app.logger.info("Content-Type: %s", request.content_type)
        
        # Verificar si hay datos multipart
        if not request.files and not request.form:
            flash("Error: No se recibieron datos del formulario", "danger")
            return redirect(url_for('ingreso_inventario'))

        # Obtener datos del formulario con valores por defecto más seguros
        nombre = request.form.get('nombre', '').strip()
        descripcion = request.form.get('descripcion', '').strip()
        precio = request.form.get('precio', '0').strip()
        stock = request.form.get('stock', '0').strip()
        lote = request.form.get('lote', '').strip()
        verificado = request.form.get('verificado', 'off') == 'on'
        categoria_id = request.form.get('categoria_id', '0').strip()
        marca_id = request.form.get('marca_id', '0').strip()
        estante = request.form.get('estante', '').strip()  # Ubicación seleccionada en el combobox
        imagen = request.files.get('imagen')

        # Buscar el id de la ubicación correspondiente al estante seleccionado
        ubicacion = UbicacionBodega.query.filter_by(estante=estante).first()
        if not ubicacion:
            flash("Error: La ubicación seleccionada no existe", "danger")
            return redirect(url_for('ingreso_inventario'))

        ubicacion_id = ubicacion.id  # Obtener el id de la ubicación

        # Depuración detallada
        app.logger.info("Datos recibidos - Nombre: %s, Precio: %s, Stock: %s, Categoría: %s, Marca: %s, Imagen: %s, Ubicación: %s",
                       nombre, precio, stock, categoria_id, marca_id, 'Sí' if imagen else 'No', ubicacion_id)

        # Validar campos obligatorios
        required_fields = {
            'nombre': nombre,
            'precio': precio,
            'stock': stock,
            'categoria_id': categoria_id,
            'marca_id': marca_id,
            'estante': estante,
            'imagen': imagen
        }

        missing_fields = [field for field, value in required_fields.items() if not value]
        
        if missing_fields:
            flash(f"Error: Faltan campos obligatorios: {', '.join(missing_fields)}", "danger")
            return redirect(url_for('ingreso_inventario'))

        # Validar tipos de datos
        try:
            precio = float(precio)
            stock = int(stock)
            categoria_id = int(categoria_id)
            marca_id = int(marca_id)
        except ValueError as e:
            flash(f"Error en los datos numéricos: {str(e)}", "danger")
            return redirect(url_for('ingreso_inventario'))

        # Subir imagen a Cloudinary
        try:
            if imagen and imagen.filename != '':
                upload_result = cloudinary.uploader.upload(imagen, folder="productos")
                imagen_url = upload_result.get("secure_url")
                app.logger.info("Imagen subida correctamente: %s", imagen_url)
            else:
                flash("Error: No se proporcionó una imagen válida", "danger")
                return redirect(url_for('ingreso_inventario'))
        except Exception as e:
            app.logger.error("Error al subir imagen: %s", str(e), exc_info=True)
            flash(f"Error al subir la imagen: {str(e)}", "danger")
            return redirect(url_for('ingreso_inventario'))

        # Crear nuevo producto con el id de la ubicación
        nuevo_producto = Producto(
            nombre=nombre,
            descripcion=descripcion,
            precio=precio,
            stock=stock,
            lote=lote,
            verificado=verificado,
            categoria_id=categoria_id,
            marca_id=marca_id,
            ubicacion_id=ubicacion_id,  # Usar ubicacion_id
            imagen=imagen_url
        )
        
        db.session.add(nuevo_producto)
        db.session.commit()
        
        flash('Producto ingresado correctamente', 'success')
        return redirect(url_for('ingreso_inventario'))

    except Exception as e:
        db.session.rollback()
        app.logger.error("Error crítico: %s", str(e), exc_info=True)
        flash(f'Error inesperado al ingresar producto: {str(e)}', 'danger')
        return redirect(url_for('ingreso_inventario'))

@app.route('/restore_producto/<int:product_id>', methods=['POST'])
def restore_producto(product_id):
    try:
        producto = Producto.query.get(product_id)
        
        if not producto:
            return jsonify({"success": False, "error": "Producto no encontrado"}), 404

        producto.activo = True
        db.session.commit()

        return jsonify({
            "success": True, 
            "message": "Producto restaurado correctamente",
            "product_id": product_id
        })

    except Exception as e:
        app.logger.error(f"Error al restaurar producto: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({
            "success": False, 
            "error": "Error interno del servidor al intentar restaurar el producto"
        }), 500
    
@app.route('/get_ubicaciones', methods=['GET'])
def get_ubicaciones():
    try:
        ubicaciones = UbicacionBodega.query.all()
        return jsonify([ubicacion.to_dict() for ubicacion in ubicaciones])
    except Exception as e:
        app.logger.error(f"Error al obtener ubicaciones: {str(e)}", exc_info=True)
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/toggle_product_status', methods=['POST'])
def toggle_product_status():
    try:
        product_id = request.args.get('id')
        producto = Producto.query.get(product_id)
        
        if not producto:
            return jsonify({"success": False, "error": "Producto no encontrado"}), 404

        # Cambiar el estado (de True a False o viceversa)
        producto.activo = not producto.activo
        db.session.commit()

        return jsonify({
            "success": True, 
            "message": "Estado del producto actualizado",
            "new_status": producto.activo
        })

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error al cambiar estado del producto: {str(e)}", exc_info=True)
        return jsonify({
            "success": False, 
            "error": "Error interno del servidor al cambiar el estado del producto"
        }), 500

@app.route('/get_all_productos', methods=['GET'])
def obtener_todos_productos():
    try:
        search_term = request.args.get('search', '').strip()
        categoria_id = request.args.get('categoria_id', type=int)
        marca_id = request.args.get('marca_id', type=int)
        
        # Consulta sin filtro por activo
        query = db.session.query(Producto)
        
        # Filtros adicionales
        if search_term:
            query = query.filter(
                db.or_(
                    Producto.nombre.ilike(f'%{search_term}%'),
                    Producto.descripcion.ilike(f'%{search_term}%'),
                    Producto.marca.has(Marca.nombre.ilike(f'%{search_term}%')),
                    Producto.categoria.has(Categoria.nombre.ilike(f'%{search_term}%'))
                )
            )
        
        if categoria_id:
            query = query.filter_by(categoria_id=categoria_id)
            
        if marca_id:
            query = query.filter_by(marca_id=marca_id)
        
        productos = query.all()
        
        productos_json = [p.to_dict() for p in productos]
        return jsonify(productos_json)
        
    except Exception as e:
        app.logger.error(f"Error al obtener productos: {str(e)}", exc_info=True)
        return jsonify({'error': 'Error interno del servidor'}), 500


# ========================== EJECUCIÓN ==========================
if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    app.run(host="0.0.0.0", port=8000, debug=debug_mode)
