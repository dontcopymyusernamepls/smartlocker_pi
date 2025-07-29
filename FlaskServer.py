from datetime import datetime, timedelta

@app.route('/locker-statistics', methods=['GET'])
def locker_statistics():
    try:
        file_path = '/home/smartlocker/stats/sensor_data.json'
        if not os.path.exists(file_path):
            return jsonify({
                "status": "error",
                "message": "Sensor data file not found"
            }), 404

        with open(file_path, 'r') as f:
            data = json.load(f)

        ir_file_path = '/home/smartlocker/stats/ir_sensor.json'
        locker_empty = None
        placed_at_str = None
        if os.path.exists(ir_file_path):
            with open(ir_file_path, 'r') as f_ir:
                ir_data = json.load(f_ir)
            locker_empty = ir_data.get("locker_empty")
            placed_at_str = ir_data.get("placed_at")

        response = {
            "status": "success",
            "temperature": data.get("temperature"),
            "humidity": data.get("humidity"),
            "timestamp": data.get("timestamp")
        }

        if locker_empty is not None:
            response["locker_empty"] = locker_empty

            if locker_empty == "No" and placed_at_str:
                placed_time = datetime.fromisoformat(placed_at_str)
                duration = datetime.now() - placed_time
                
                # For real usage, use: threshold = timedelta(days=3)
                # For simulation, use 30 seconds threshold:
                threshold = timedelta(seconds=30)
                
                if duration > threshold:
                    response["message"] = "Parcel not collected for 3 days"

        return jsonify(response)

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
