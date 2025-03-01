from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Enum

# ========================== MODELO DE USUARIOS ==========================

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    correo = db.Column(db.String(120), unique=True, nullable=False)
    nombre = db.Column(db.String(50), nullable=False)
    apellidos = db.Column(db.String(50), nullable=False)
    contraseña = db.Column(db.String(200), nullable=False)  # Contraseña hasheada
    es_admin = db.Column(db.Boolean, default=False)
    
    def set_password(self, contraseña):
        self.contraseña = generate_password_hash(contraseña)
    
    def check_password(self, contraseña):
        return check_password_hash(self.contraseña, contraseña)
    
    def __repr__(self):
        return f"<Usuario {self.nombre} {self.apellidos}>"


# ========================== MODELO DE MARCAS ==========================

class Marca(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)

    def __repr__(self):
        return f"<Marca {self.nombre}>"


# ========================== MODELO DE CATEGORÍAS ==========================

class Categoria(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    
    def __repr__(self):
        return f"<Categoria {self.nombre}>"


# ========================== MODELO DE PRODUCTOS ==========================

class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    precio = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    imagen = db.Column(db.String(255), nullable=True)  # Ruta relativa de la imagen

    categoria_id = db.Column(db.Integer, db.ForeignKey('categoria.id', ondelete="CASCADE"), nullable=False)
    marca_id = db.Column(db.Integer, db.ForeignKey('marca.id', ondelete="CASCADE"), nullable=False)

    categoria = db.relationship('Categoria', backref=db.backref('productos', lazy=True, cascade="all, delete-orphan"))
    marca = db.relationship('Marca', backref=db.backref('productos', lazy=True, cascade="all, delete-orphan"))

    def __repr__(self):
        return f"<Producto {self.nombre} - ${self.precio}>"


# ========================== MODELO DE PEDIDOS ==========================

ESTADOS_PEDIDO = ('Pendiente', 'Pagado', 'Enviado', 'Entregado', 'Cancelado')

class Pedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id', ondelete="CASCADE"), nullable=False)
    fecha = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    total = db.Column(db.Float, nullable=False)
    estado = db.Column(Enum(*ESTADOS_PEDIDO, name="estado_pedido"), nullable=False, default='Pendiente')

    usuario = db.relationship('Usuario', backref=db.backref('pedidos', lazy=True, cascade="all, delete-orphan"))

    def __repr__(self):
        return f"<Pedido {self.id} - Usuario {self.usuario_id} - Estado {self.estado}>"


# ========================== MODELO DE DETALLES DE PEDIDO ==========================

class DetallePedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedido.id', ondelete="CASCADE"), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id', ondelete="CASCADE"), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False, default=1)
    precio_unitario = db.Column(db.Float, nullable=False)

    pedido = db.relationship('Pedido', backref=db.backref('detalles', lazy=True, cascade="all, delete-orphan"))
    producto = db.relationship('Producto', backref=db.backref('detalles', lazy=True, cascade="all, delete-orphan"))

    def __repr__(self):
        return f"<DetallePedido Pedido {self.pedido_id} - Producto {self.producto_id} - Cantidad {self.cantidad}>"
