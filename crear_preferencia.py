import requests
import json

def crear_preferencia_carrito(carrito):
    # URL de la API de Mercado Pago
    url = "https://api.mercadopago.com/checkout/preferences"

    # Tu Access Token de Producción (PROD-...)
    access_token = "APP_USR-7356850175082371-050708-0ef8768d3184ead8d91f27da42a86ac0-466327316"

    # Los headers necesarios para la autenticación
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # Datos de la preferencia de pago
    payload = {
        "items": carrito,
        "back_urls": {
            "success": "https://labodegadeldeporte-production.up.railway.app/pago_exitoso",
            "failure": "https://labodegadeldeporte-production.up.railway.app/pago_fallido",
            "pending": "https://labodegadeldeporte-production.up.railway.app/pago_pendiente"
        },
        "auto_return": "approved"
    }

    # Hacemos la solicitud POST para crear la preferencia
    response = requests.post(url, headers=headers, data=json.dumps(payload))

    # Comprobamos si la respuesta fue exitosa
    if response.status_code == 201:
        # Obtenemos la respuesta JSON
        preference_response = response.json()

        # Retornamos el init_point de la preferencia para la redirección
        return preference_response["response"]["init_point"], None
    else:
        # Si hubo un error, retornamos el error
        return None, f"Error al crear la preferencia: {response.text}"




