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

class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    precio = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    imagen = db.Column(db.String(255))
    categoria_id = db.Column(db.Integer, db.ForeignKey('categoria.id'), nullable=False)  # Nueva columna
    marca_id = db.Column(db.Integer, db.ForeignKey('marca.id'), nullable=False)          # Nueva columna

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
            'marca_id': self.marca_id
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
            print("Error: El contenido no es multipart/form-data")
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

        # Imprimir los valores recibidos para depuración
        print(f"Producto ID: {producto_id}")
        print(f"Nombre: {nombre}")
        print(f"Descripción: {descripcion}")
        print(f"Precio: {precio}")
        print(f"Stock: {stock}")
        print(f"Categoría ID: {categoria_id}")
        print(f"Marca ID: {marca_id}")
        print(f"Imagen: {imagen}")

        # Obtener el producto existente
        producto = Producto.query.get(producto_id)
        if not producto:
            return jsonify({'success': False, 'error': 'Producto no encontrado'}), 404

        # Actualizar los datos del producto
        producto.nombre = nombre
        producto.descripcion = descripcion
        producto.precio = precio
        producto.stock = stock
        producto.categoria_id = categoria_id
        producto.marca_id = marca_id

        # Si hay una nueva imagen, subirla a Cloudinary
        if imagen:
            try:
                upload_result = cloudinary.uploader.upload(imagen, folder=f"productos/{producto.id}")
                producto.imagen = upload_result.get("secure_url")
                print(f"Imagen subida a Cloudinary: {producto.imagen}")
            except Exception as e:
                print(f"Error al subir la imagen a Cloudinary: {str(e)}")
                return jsonify({'success': False, 'error': 'Error al subir la imagen'}), 500

        # Guardar los cambios en la base de datos
        try:
            db.session.commit()
            print("Producto actualizado y guardado en la base de datos")
        except Exception as e:
            print(f"Error al guardar el producto en la base de datos: {str(e)}")
            return jsonify({'success': False, 'error': 'Error al guardar en la base de datos'}), 500

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
        
        query = db.session.query(Producto)
        
        # Filtros
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
        
        # Usar el método to_dict() que hemos definido
        productos_json = [p.to_dict() for p in productos]
        return jsonify(productos_json)
        
    except Exception as e:
        app.logger.error(f"Error al obtener productos: {str(e)}", exc_info=True)
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


@app.route('/get_marcas/<int:categoria_id>')
def get_marcas(categoria_id):
    categoria_obj = Categoria.query.get(categoria_id)
    marcas = categoria_obj.marcas if categoria_obj else []
    
    return render_template('marcas_dropdown.html', marcas=marcas)

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
        "descripcion": producto.descripcion,
        "precio": producto.precio,
        "stock": producto.stock,
        "imagen": producto.imagen,  # Incluir la URL de la imagen
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

@app.route('/pago')
def pago():
    carrito = session.get('carrito', [])
    total = sum(producto['precio'] * producto['cantidad'] for producto in carrito)
    return render_template('pago.html', carrito=carrito, total=total)


@app.route('/admin_inventario')
def inventario():
    productos = Producto.query.all()
    return render_template('admin_inventario.html', productos=productos)


# ========================== EJECUCIÓN ==========================
if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    app.run(host="0.0.0.0", port=8000, debug=debug_mode)
