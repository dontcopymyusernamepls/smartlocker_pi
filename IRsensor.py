from flask import Flask, request, jsonify
import os
import json
import time

app = Flask(__name__)

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

        return jsonify(response)

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
