from app import create_app, db

"""
Este archivo es el encargado de eliminar y crear la base de datos desde cero.
Sirve para cuando se necesite reiniciar la base de datos y se quiere hacer de forma automática.
Se ejecuta desde la terminal con el comando python reset_db.py
Se debe tener en cuenta que este archivo no se debe ejecutar en
entornos de producción, ya que se perderán todos los datos de la base de datos.
Para entornos de producción se recomienda realizar un backup de la base de datos antes de ejecutar este archivo.
"""
app = create_app()

with app.app_context():
    db.drop_all()  # Elimina todas las tablas
    db.create_all()  # Crea las tablas de nuevo
    print("✅ Base de datos eliminada y creada desde cero.")
