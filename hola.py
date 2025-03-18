from main import db, app

"""
Este script se encarga de crear las tablas en la base de datos
"""
with app.app_context():
    db.create_all()
    print("Tablas creadas correctamente")