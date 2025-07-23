from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)
shared_data = {'pin': '111111'}  # Default PIN

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
        file_path = '/home/smartlocker/stats/sensor_data.json'
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                data = json.load(f)
            return jsonify({
                "status": "success",
                "temperature": data.get("temperature"),
                "humidity": data.get("humidity"),
                "timestamp": data.get("timestamp")
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Sensor data file not found"
            }), 404
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
