from app import create_app, db
from app.models import Usuario

# Crear la aplicación
app = create_app()

# Establecer el contexto de la aplicación
with app.app_context():
    # Crear el usuario
    usuario = Usuario(
        correo="chatcito77@gmail.com",
        nombre="John",
        apellidos="Cena"
    )
    usuario.set_password("1234")  # Hashear la contraseña

    # Agregarlo a la base de datos
    db.session.add(usuario)
    db.session.commit()

    print("Usuario creado exitosamente.")
