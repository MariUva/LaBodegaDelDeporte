from app import create_app, db
from app.models import Producto

# Crear la aplicación
app = create_app()

# Establecer el contexto de la aplicación
with app.app_context():
    # Crear productos para cada categoría
    productos = [
        # Balones
        Producto(nombre="Balón Nike Strike", descripcion="Balón de fútbol profesional", precio=79.99, stock=20, categoria_id=1, marca_id=1),
        Producto(nombre="Balón Adidas Tango", descripcion="Balón oficial de entrenamientos", precio=69.99, stock=15, categoria_id=1, marca_id=2),
        Producto(nombre="Balón Puma Future", descripcion="Balón de alta resistencia", precio=59.99, stock=10, categoria_id=1, marca_id=3),

        # Ropa Mujer
        Producto(nombre="Camiseta Nike Dri-FIT", descripcion="Camiseta deportiva con tecnología Dri-FIT", precio=49.99, stock=25, categoria_id=2, marca_id=1),
        Producto(nombre="Leggings Adidas Performance", descripcion="Leggings de entrenamiento de alta elasticidad", precio=54.99, stock=30, categoria_id=2, marca_id=2),
        Producto(nombre="Sudadera Puma Sport", descripcion="Sudadera cómoda y ligera para entrenar", precio=59.99, stock=18, categoria_id=2, marca_id=3),

        # Ropa Hombre
        Producto(nombre="Camiseta Nike Dry", descripcion="Camiseta deportiva para hombres", precio=44.99, stock=22, categoria_id=3, marca_id=1),
        Producto(nombre="Pantalón Adidas ClimaCool", descripcion="Pantalón deportivo transpirable", precio=64.99, stock=19, categoria_id=3, marca_id=2),
        Producto(nombre="Chaqueta Puma Training", descripcion="Chaqueta térmica para entrenamientos", precio=74.99, stock=15, categoria_id=3, marca_id=3),

        # Tenis
        Producto(nombre="Nike Air Zoom Pegasus", descripcion="Zapatillas para correr con amortiguación", precio=129.99, stock=10, categoria_id=4, marca_id=1),
        Producto(nombre="Adidas Ultraboost", descripcion="Zapatillas de running con tecnología Boost", precio=149.99, stock=12, categoria_id=4, marca_id=2),
        Producto(nombre="Puma Velocity Nitro", descripcion="Zapatillas ligeras para entrenamientos intensivos", precio=119.99, stock=8, categoria_id=4, marca_id=3),
    ]

    # Agregar y confirmar cambios en la base de datos
    db.session.bulk_save_objects(productos)
    db.session.commit()

    print("✅ Productos creados exitosamente.")
