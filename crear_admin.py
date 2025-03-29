from main import app, db  
from main import Usuario  
from werkzeug.security import generate_password_hash

# Crear el contexto de la aplicación
with app.app_context():
    # Buscar si el usuario ya existe en la BD
    admin_existente = Usuario.query.filter_by(correo="andersonchuly@gmail.com").first()
    
    if admin_existente:
        if not admin_existente.es_admin:
            # Si el usuario existe pero no es admin, lo actualizamos
            admin_existente.es_admin = True
            db.session.commit()
            print("El usuario existente fue actualizado a administrador.")
        else:
            print("El usuario administrador ya existe.")
    else:
        # Crear un nuevo usuario administrador si no existe
        nuevo_admin = Usuario(
            nombre="Admin",
            apellidos="Sistema",
            correo="andersonchuly@gmail.com",
            contraseña=generate_password_hash("admin123"),  
            es_admin=True  
        )

        db.session.add(nuevo_admin)
        db.session.commit()
        print("Administrador creado con éxito.")
