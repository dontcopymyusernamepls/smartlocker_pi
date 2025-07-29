from flask import Flask, request, jsonify
import json
import os
import paho.mqtt.client as mqtt

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
        # Read main sensor data (temperature, humidity, timestamp)
        file_path = '/home/smartlocker/stats/sensor_data.json'
        if not os.path.exists(file_path):
            return jsonify({
                "status": "error",
                "message": "Sensor data file not found"
            }), 404

        with open(file_path, 'r') as f:
            data = json.load(f)

        # Read IR sensor data (locker empty yes/no)
        ir_file_path = '/home/smartlocker/stats/ir_sensor.json'
        locker_empty = None
        if os.path.exists(ir_file_path):
            with open(ir_file_path, 'r') as f_ir:
                ir_data = json.load(f_ir)
            locker_empty = ir_data.get("locker_empty")
        
        # Build response including locker_empty if found
        response = {
            "status": "success",
            "temperature": data.get("temperature"),
            "humidity": data.get("humidity"),
            "timestamp": data.get("timestamp")
        }
        
        if locker_empty is not None:
            response["locker_empty"] = locker_empty

        return jsonify(response)

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
