from flask import Flask, request, jsonify
import json
import os
import paho.mqtt.client as mqtt
from datetime import datetime, timedelta  # <-- imported for date checking

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
        # Read main sensor data
        file_path = '/home/smartlocker/stats/sensor_data.json'
        if not os.path.exists(file_path):
            return jsonify({
                "status": "error",
                "message": "Sensor data file not found"
            }), 404

        with open(file_path, 'r') as f:
            data = json.load(f)

        # Read IR sensor data
        ir_file_path = '/home/smartlocker/stats/ir_sensor.json'
        locker_empty = "-"
        placed_at_str = None
        message = None

        if os.path.exists(ir_file_path):
            with open(ir_file_path, 'r') as f_ir:
                ir_data = json.load(f_ir)
            locker_empty = ir_data.get("locker_empty", "-")
            placed_at_str = ir_data.get("placed_at")

        # Check for parcel delay (3 days or 30 sec for testing)
        if locker_empty == "No" and placed_at_str:
            try:
                placed_time = datetime.fromisoformat(placed_at_str)
                if (datetime.now() - placed_time) > timedelta(seconds=30):  # ← change to days=3 in production
                    message = "Parcel not collected for 3 days"
            except Exception as e:
                print(f"[!] Timestamp parsing error: {e}")

        # Build response
        response = {
            "status": "success",
            "temperature": data.get("temperature"),
            "humidity": data.get("humidity"),
            "timestamp": data.get("timestamp"),
            "locker_empty": locker_empty
        }

        if message:
            response["message"] = message

        return jsonify(response)

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
