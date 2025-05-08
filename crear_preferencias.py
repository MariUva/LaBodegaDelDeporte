from flask import Flask, request, jsonify
import mercadopago

app = Flask(__name__)

# Reemplaza con tu Access Token de prueba o producción
sdk = mercadopago.SDK("APP_USR-7356850175082371-050708-0ef8768d3184ead8d91f27da42a86ac0-466327316")

@app.route('/crear_preferencia', methods=['POST'])
def crear_preferencia():
    # Obtener los productos enviados desde el frontend (carrito)
    carrito = request.json.get('items', [])

    # Verificar si el carrito no está vacío
    if not carrito:
        return jsonify({"error": "El carrito está vacío"}), 400

    # Crea la preferencia de pago con los productos del carrito
    preference_data = {
        "items": carrito,
        "back_urls": {
            "success": "https://labodegadeldeporte-production.up.railway.app/exito",
            "failure": "https://labodegadeldeporte-production.up.railway.app/error",
            "pending": "https://labodegadeldeporte-production.up.railway.app/pendiente"
        },
        "auto_return": "approved"
    }

    # Crear la preferencia en Mercado Pago
    preference_response = sdk.preference().create(preference_data)

    # Retornar el enlace de pago (init_point)
    if preference_response["status"] == 201:  # Verifica que se haya creado correctamente
        return jsonify({
            "init_point": preference_response["response"]["init_point"]
        })
    else:
        return jsonify({"error": "Error al crear la preferencia de pago"}), 500
