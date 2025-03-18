from app import create_app, db
from app.models import Categoria, Marca

# Crear la aplicación
app = create_app()

# Establecer el contexto de la aplicación
with app.app_context():
    # Crear categorías
    categorias = [
        Categoria(id=1, nombre="Balones"),
        Categoria(id=2, nombre="Ropa mujer"),
        Categoria(id=3, nombre="Ropa hombre"),
        Categoria(id=4, nombre="Tenis"),
    ]

    # Crear marcas
    marcas = [
        Marca(id=1, nombre="Nike"),
        Marca(id=2, nombre="Adidas"),
        Marca(id=3, nombre="Puma"), 
         
    ]

    # Agregar y confirmar cambios en la base de datos
    db.session.bulk_save_objects(categorias)
    db.session.bulk_save_objects(marcas)
    db.session.commit()

    print("✅ Categorías y marcas creadas exitosamente.")
