from flask import Flask, request, jsonify
import adafruit_dht
import board

app = Flask(__name__)
shared_data = {'pin': '111111'}  # Default PIN

# Initialize DHT11 sensor (GPIO 4 / D4)
dht_device = adafruit_dht.DHT11(board.D4)

# ========== PIN APIs ==========
@app.route('/set-pin', methods=['POST'])
def set_pin():
    data = request.get_json()
    new_pin = data.get('pin')
    if new_pin and len(new_pin) == 6:
        shared_data['pin'] = new_pin
        return {'status': 'success', 'pin': new_pin}
    return {'status': 'error', 'message': 'Invalid pin'}, 400

@app.route('/get-pin', methods=['GET'])
def get_pin():
    return {'pin': shared_data['pin']}


# ========== Locker Statistics API ==========
@app.route('/locker-statistics', methods=['GET'])
def locker_statistics():
    try:
        temperature = dht_device.temperature
        humidity = dht_device.humidity

        if temperature is not None and humidity is not None:
            return jsonify({
                "status": "success",
                "temperature": temperature,
                "humidity": humidity
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Sensor reading not available"
            }), 500

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
