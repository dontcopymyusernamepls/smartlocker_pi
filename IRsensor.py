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
            "timestamp": data.get("timestamp"),
            "locker_empty": locker_empty
        }
