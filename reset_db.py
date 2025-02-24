from app import create_app, db

app = create_app()

with app.app_context():
    db.drop_all()  # Elimina todas las tablas
    db.create_all()  # Crea las tablas de nuevo
    print("✅ Base de datos eliminada y creada desde cero.")
