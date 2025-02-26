from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Enum
import enum
from enum import Enum as PyEnum
from sqlalchemy import CheckConstraint
from datetime import datetime
from sqlalchemy.orm import validates
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.orm import relationship

# ========================== MODELO DE USUARIOS ==========================

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # "_id" en MongoDB
    nombre = db.Column(db.String(50), nullable=False)
    apellido = db.Column(db.String(50), nullable=False)
    correo = db.Column(db.String(120), unique=True, nullable=False, index=True)  # Índice para búsquedas rápidas
    password = db.Column(db.String(200), nullable=False, repr=False)  # No exponer en consultas
    rol = db.Column(db.Enum('administrador', 'cliente', name="rol_usuario"), nullable=False, default='cliente')
    direccion = db.Column(db.String(255), nullable=True)
    telefono = db.Column(db.String(20), nullable=True)
    fecha_de_registro = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())

    def set_password(self, password):
        """Hashea la contraseña antes de guardarla."""
        self.password = generate_password_hash(str(password))

    def check_password(self, password):
        """Verifica si la contraseña ingresada coincide con la almacenada."""
        return check_password_hash(self.password, password)

    def es_admin(self):
        """Devuelve True si el usuario es administrador."""
        return self.rol == 'administrador'

    def __repr__(self):
        return f"<Usuario {self.nombre} {self.apellido} - {self.rol}>"

# ========================== MODELO DE CARRITO ==========================
class Carrito(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id', ondelete="CASCADE"), nullable=False)
    fecha = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    usuario = db.relationship('Usuario', backref=db.backref('carritos', lazy='joined', cascade="all, delete-orphan"))

class CarritoProducto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    carrito_id = db.Column(db.Integer, db.ForeignKey('carrito.id', ondelete="CASCADE"), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id', ondelete="CASCADE"), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False, default=1)

    carrito = db.relationship('Carrito', backref=db.backref('productos_carrito', lazy='joined', cascade="all, delete-orphan"))
    producto = db.relationship('Producto', backref=db.backref('en_carritos', lazy='joined'))

    # Validación de cantidad mínima
    @validates('cantidad')
    def validate_cantidad(self, key, value):
        if value < 1:
            raise ValueError("La cantidad debe ser al menos 1")
        return value

# ========================== MODELO DE PRODUCTOS ==========================

class TipoProductoEnum(Enum):
    ZAPATO = "Zapato"
    CAMISA = "Camisa"
    PANTALONETA = "Pantaloneta"
    GORRA = "Gorra"
    BALON = "Balon"

class MarcaEnum(Enum):
    NIKE = "Nike"
    ADIDAS = "Adidas"
    PUMA = "Puma"
    REEBOK = "Reebok"
    UNDER_ARMOUR = "Under Armour"

class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    precio = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    imagen = db.Column(db.String(255), nullable=True)

    tipo_producto = db.Column(db.Enum(TipoProductoEnum, native_enum=False, name="tipo_producto_enum"), nullable=False)  
    marca = db.Column(db.Enum(MarcaEnum, native_enum=False, name="marca_enum"), nullable=False)

    @validates('precio', 'stock')
    def validate_numeros_positivos(self, key, value):
        if value < 0:
            raise ValueError(f"{key.capitalize()} no puede ser negativo.")
        return value

    def __repr__(self):
        return f"<Producto {self.nombre} - {self.tipo_producto.value} - {self.marca.value} - ${self.precio}>"

# ========================== MODELO DE Sub-PRODUCTOS ==========================

# ✅ Definición de los Enum
class TallaEnum(Enum):
    S = "S"
    M = "M"
    L = "L"
    XL = "XL"

class EstiloCamisaEnum(Enum):
    MANGA_CORTA = "manga_corta"
    MANGA_LARGA = "manga_larga"
    SIN_MANGA = "sin_manga"

class SexoEnum(Enum):
    HOMBRE = "hombre"
    MUJER = "mujer"

class TipoGorraEnum(Enum):
    SNAPBACK = "snapback"
    BEISBOLERA = "beisbolera"
    TRUCKER = "trucker"
    PLANA = "plana"

class EstiloPantalonetaEnum(Enum):
    DEPORTIVA = "deportiva"
    CASUAL = "casual"
    NATACION = "natacion"

class TipoBalonEnum(Enum):
    FUTBOL = "futbol"
    MICROFUTBOL = "microfutbol"
    BALONCESTO = "baloncesto"
    VOLEIBOL = "voleibol"
    TENIS = "tenis"

class MaterialEnum(Enum):
    AAA = "AAA"
    NACIONAL = "nacional"

# ✅ Modelo Base Producto
class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    precio = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    imagen = db.Column(db.String(255), nullable=True)

    tipo_producto = db.Column(db.Enum(TipoBalonEnum, native_enum=False, name="tipo_producto_enum"), nullable=False)

    __mapper_args__ = {
        "polymorphic_identity": "producto",
        "polymorphic_on": tipo_producto
    }

    @validates('precio', 'stock')
    def validate_numeros_positivos(self, key, value):
        if value < 0:
            raise ValueError(f"{key.capitalize()} no puede ser negativo.")
        return value

# ✅ Modelo Zapato
class Zapato(Producto):
    id = db.Column(db.Integer, db.ForeignKey('producto.id'), primary_key=True)
    talla = db.Column(db.Integer, nullable=False)
    color = db.Column(db.String(50), nullable=False)
    material = db.Column(db.Enum(MaterialEnum, native_enum=False, name="material_enum"), nullable=False)
    sexo = db.Column(db.Enum(SexoEnum, native_enum=False, name="sexo_enum"), nullable=False)

    __mapper_args__ = {
        "polymorphic_identity": "zapato"
    }

    __table_args__ = (
        CheckConstraint('talla BETWEEN 36 AND 46', name='check_talla_rango'),
    )

    def __init__(self, talla, *args, **kwargs):
        if talla < 36 or talla > 46:
            raise ValueError("La talla debe estar entre 36 y 46")
        super().__init__(talla=talla, *args, **kwargs)

# ✅ Modelo Camisa
class Camisa(Producto):
    id = db.Column(db.Integer, db.ForeignKey('producto.id'), primary_key=True)
    talla = db.Column(db.Enum(TallaEnum, native_enum=False, name="talla_enum"), nullable=False)
    color = db.Column(db.String(50), nullable=False)
    estilo = db.Column(db.Enum(EstiloCamisaEnum, native_enum=False, name="estilo_camisa_enum"), nullable=False)
    sexo = db.Column(db.Enum(SexoEnum, native_enum=False, name="sexo_enum"), nullable=False)

    __mapper_args__ = {
        "polymorphic_identity": "camisa"
    }

# ✅ Modelo Gorra
class Gorra(Producto):
    id = db.Column(db.Integer, db.ForeignKey('producto.id'), primary_key=True)
    talla = db.Column(db.Enum(TallaEnum, native_enum=False, name="talla_enum"), nullable=False)
    color = db.Column(db.String(50), nullable=False)
    tipo_gorra = db.Column(db.Enum(TipoGorraEnum, native_enum=False, name="tipo_gorra_enum"), nullable=False)

    __mapper_args__ = {
        "polymorphic_identity": "gorra"
    }

# ✅ Modelo Pantaloneta
class Pantaloneta(Producto):
    id = db.Column(db.Integer, db.ForeignKey('producto.id'), primary_key=True)
    talla = db.Column(db.Enum(TallaEnum, native_enum=False, name="talla_enum"), nullable=False)
    color = db.Column(db.String(50), nullable=False)
    estilo = db.Column(db.Enum(EstiloPantalonetaEnum, native_enum=False, name="estilo_pantaloneta_enum"), nullable=False)

    __mapper_args__ = {
        "polymorphic_identity": "pantaloneta"
    }

# ✅ Modelo Balon
class Balon(Producto):
    id = db.Column(db.Integer, db.ForeignKey('producto.id'), primary_key=True)
    tipo_balon = db.Column(db.Enum(TipoBalonEnum, native_enum=False, name="tipo_balon_enum"), nullable=False)
    color = db.Column(db.String(50), nullable=False)

    __mapper_args__ = {
        "polymorphic_identity": "balon"
    }

# ========================== MODELO DE PEDIDOS ==========================

class EstadoPedidoEnum(PyEnum):
    PENDIENTE = "Pendiente"
    ENVIADO = "Enviado"
    ENTREGADO = "Entregado"
    CANCELADO = "Cancelado"

class Pedido(db.Model):
    __tablename__ = "pedido"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id', ondelete="CASCADE"), nullable=False, index=True)
    fecha = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    total = db.Column(db.Float, nullable=False, default=0.0)
    estado = db.Column(SQLAlchemyEnum(EstadoPedidoEnum, name="estado_pedido_enum"), 
                       nullable=False, 
                       default=lambda: EstadoPedidoEnum.PENDIENTE)
    direccion_envio = db.Column(db.String(255), nullable=False)

    usuario = relationship('Usuario', backref=db.backref('pedidos', lazy=True, cascade="all, delete-orphan"))

    __table_args__ = (
        CheckConstraint('total >= 0', name='check_total_no_negativo'),
    )

    def cambiar_estado(self, nuevo_estado):
        """Cambia el estado del pedido asegurando transiciones válidas."""
        transiciones_validas = {
            EstadoPedidoEnum.PENDIENTE: [EstadoPedidoEnum.ENVIADO, EstadoPedidoEnum.CANCELADO],
            EstadoPedidoEnum.ENVIADO: [EstadoPedidoEnum.ENTREGADO, EstadoPedidoEnum.CANCELADO],
            EstadoPedidoEnum.ENTREGADO: [],
            EstadoPedidoEnum.CANCELADO: []
        }

        if nuevo_estado not in transiciones_validas[self.estado]:
            raise ValueError(f"No se puede cambiar el estado de {self.estado.value} a {nuevo_estado.value}")

        self.estado = nuevo_estado

    def __repr__(self):
        return f"<Pedido {self.id} - Usuario {self.usuario_id} - Estado {self.estado.value}>"

# ========================== MODELO DE DETALLES DE PEDIDO ==========================

class DetallePedido(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedido.id', ondelete="CASCADE"), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id', ondelete="CASCADE"), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False, default=1)
    precio_unitario = db.Column(db.Float, nullable=False)

    pedido = db.relationship('Pedido', backref=db.backref('detalles', lazy=True, cascade="all, delete-orphan"))
    producto = db.relationship('Producto', backref=db.backref('detalles', lazy=True))

    __table_args__ = (
        db.CheckConstraint('cantidad > 0', name='check_cantidad_positiva'),
        db.CheckConstraint('precio_unitario >= 0', name='check_precio_no_negativo'),
    )

    def calcular_subtotal(self):
        """Calcula el subtotal del detalle del pedido."""
        return self.cantidad * self.precio_unitario

    def __repr__(self):
        return f"<DetallePedido Pedido {self.pedido_id} - Producto {self.producto_id} - Cantidad {self.cantidad} - Subtotal {self.calcular_subtotal():.2f}>"
# ================================= MODELO DE REGISTRO ===================================

class TipoAccionEnum(PyEnum):
    REGISTRO = "registro"
    INICIO_SESION = "inicio_sesion"
    COMPRA = "compra"
    CAMBIO_ESTADO_PEDIDO = "cambio_estado_pedido"
    ACTUALIZACION_PERFIL = "actualizacion_perfil"

class RegistroActividad(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id', ondelete="CASCADE"), nullable=False, index=True)
    accion = db.Column(db.Enum(TipoAccionEnum, name="tipo_accion_enum"), nullable=False)
    detalle = db.Column(db.String(255), nullable=True)
    fecha = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    usuario = db.relationship('Usuario', backref=db.backref('actividades', lazy=True, cascade="all, delete-orphan"))

    __table_args__ = (
        db.CheckConstraint("LENGTH(TRIM(detalle)) > 0 OR detalle IS NULL", name="check_detalle_no_vacio"),
    )

    def __init__(self, usuario_id, accion, detalle=None):
        self.usuario_id = usuario_id
        self.accion = accion
        self.detalle = detalle.strip() if detalle and detalle.strip() else None

    def __repr__(self):
        return f"<RegistroActividad Usuario {self.usuario_id} - Acción {self.accion.value} - {self.fecha}>"
# ================================= MODELO DE PAGO ========================================

class MetodoPagoEnum(PyEnum):
    TARJETA = "tarjeta"
    PAYPAL = "paypal"
    TRANSFERENCIA_BANCARIA = "transferencia_bancaria"

class EstadoPagoEnum(PyEnum):
    PENDIENTE = "pendiente"
    COMPLETADO = "completado"
    FALLIDO = "fallido"

class Pago(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedido.id', ondelete="CASCADE"), nullable=False, index=True)
    fecha = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    monto = db.Column(db.Float, nullable=False)
    metodo = db.Column(db.Enum(MetodoPagoEnum, name="metodo_pago_enum"), nullable=False)
    estado_pago = db.Column(db.Enum(EstadoPagoEnum, name="estado_pago_enum"), nullable=False, default=EstadoPagoEnum.PENDIENTE)
    codigo_transaccion = db.Column(db.String(100), nullable=True)

    pedido = db.relationship('Pedido', backref=db.backref('pagos', lazy=True, cascade="all, delete-orphan"))

    __table_args__ = (
        db.CheckConstraint("monto >= 0", name="check_monto_no_negativo"),
        db.CheckConstraint("LENGTH(TRIM(codigo_transaccion)) > 0 OR codigo_transaccion IS NULL", name="check_codigo_transaccion"),
    )

    def __init__(self, pedido_id, monto, metodo, estado_pago=EstadoPagoEnum.PENDIENTE, codigo_transaccion=None):
        self.pedido_id = pedido_id
        self.monto = max(0, monto)  # Asegura que el monto no sea negativo
        self.metodo = metodo
        self.estado_pago = estado_pago
        self.codigo_transaccion = codigo_transaccion.strip() if codigo_transaccion and codigo_transaccion.strip() else None

    def __repr__(self):
        return f"<Pago Pedido {self.pedido_id} - Monto ${self.monto} - Estado {self.estado_pago.value}>"

