from flask import Flask, request, jsonify, make_response
import json
import os
import datetime
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
        # Initialize response with default values
        response = {
            "status": "success",
            "temperature": None,
            "humidity": None,
            "timestamp": time.time(),
            "locker_empty": None,
            "message": ""  # Always include message field
        }

        # Read sensor data
        sensor_file = '/home/smartlocker/stats/sensor_data.json'
        if os.path.exists(sensor_file) and os.path.getsize(sensor_file) > 0:
            with open(sensor_file, 'r') as f:
                try:
                    sensor_data = json.load(f)
                    response.update({
                        "temperature": sensor_data.get("temperature"),
                        "humidity": sensor_data.get("humidity"),
                        "timestamp": sensor_data.get("timestamp", time.time())
                    })
                except json.JSONDecodeError:
                    print("[Flask] sensor_data.json is invalid.")
                    response["message"] = "Error reading sensor data."

        # Read IR sensor data
        ir_file = '/home/smartlocker/stats/ir_sensor.json'
        if os.path.exists(ir_file) and os.path.getsize(ir_file) > 0:
            with open(ir_file, 'r') as f:
                try:
                    ir_data = json.load(f)
                    response["locker_empty"] = ir_data.get("locker_empty", "")
                    response["message"] = ir_data.get("message", "")
                except json.JSONDecodeError:
                    print("[Flask] ir_sensor.json is invalid JSON.")
                    response["message"] = "Error reading IR sensor data."
        else:
            print("[Flask] ir_sensor.json is missing or empty.")
            response["message"] = "No IR sensor data found."

        # Final log
        print("[Flask] Final response:", response)

        return make_response(json.dumps(response), 200, {'Content-Type': 'application/json'})
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
        
# ========== Main ==========
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
