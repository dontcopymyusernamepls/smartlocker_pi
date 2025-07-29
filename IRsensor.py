@app.route('/locker-statistics', methods=['GET'])
def locker_statistics():
    try:
        # Read main sensor data
        sensor_file = '/home/smartlocker/stats/sensor_data.json'
        ir_file = '/home/smartlocker/stats/ir_sensor.json'
        
        # Initialize response with default values
        response = {
            "status": "success",
            "temperature": None,
            "humidity": None,
            "timestamp": time.time(),
            "locker_empty": None,
            "message": None
        }

        # Read temperature/humidity if available
        if os.path.exists(sensor_file):
            with open(sensor_file, 'r') as f:
                sensor_data = json.load(f)
            response.update({
                "temperature": sensor_data.get("temperature"),
                "humidity": sensor_data.get("humidity")
            })

        # Read IR sensor data if available
        if os.path.exists(ir_file):
            with open(ir_file, 'r') as f:
                ir_data = json.load(f)
            response.update({
                "locker_empty": ir_data.get("locker_empty"),
                "message": ir_data.get("message", "")
            })

        return jsonify(response)

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
