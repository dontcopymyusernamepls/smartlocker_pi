from flask import Flask, jsonify
import json
import os

app = Flask(__name__)

# File paths
stats_file_path = "/home/smartlocker/stats/stats.json"
ir_status_file_path = "/home/smartlocker/stats/ir_status.json"

@app.route('/locker-statistics', methods=['GET'])
def locker_statistics():
    response = {"status": "success"}

    # Load temp/humidity
    try:
        if os.path.exists(stats_file_path):
            with open(stats_file_path, 'r') as f:
                stats = json.load(f)
            response["temperature"] = stats.get("temperature")
            response["humidity"] = stats.get("humidity")
        else:
            response["temperature"] = None
            response["humidity"] = None
    except Exception as e:
        response["temperature"] = None
        response["humidity"] = None
        response["temp_humidity_error"] = str(e)

    # Load IR sensor presence
    try:
        if os.path.exists(ir_status_file_path):
            with open(ir_status_file_path, 'r') as f:
                ir_data = json.load(f)
            response["parcel_present"] = ir_data.get("parcel_present", False)
        else:
            response["parcel_present"] = False
    except Exception as e:
        response["parcel_present"] = False
        response["ir_sensor_error"] = str(e)

    return jsonify(response)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
