import mercadopago

# Reemplaza con tu Access Token de prueba o producción
sdk = mercadopago.SDK("TEST-7356850175082371-050708-a469ce66523a2bd689849769538245a7-466327316")

# Crea la preferencia
preference_data = {
    "items": [
        {
            "title": "Camiseta de fútbol",
            "quantity": 1,
            "unit_price": 100.0,
            "currency_id": "COP"  # O "USD", "ARS", etc.
        }
    ],
    "back_urls": {
        "success": "https://www.tusitio.com/exito",
        "failure": "https://www.tusitio.com/error",
        "pending": "https://www.tusitio.com/pendiente"
    },
    "auto_return": "approved"
}

# Ejecutar la creación
preference_response = sdk.preference().create(preference_data)

# Mostrar el enlace de pago
print("Enlace de pago:", preference_response["response"]["init_point"])
