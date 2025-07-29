def ir_sensor_loop():
    last_state = None
    while True:
        current_state = GPIO.input(IR_SENSOR_PIN)
        state_str = "No" if current_state == 0 else "Yes"  # No = full, Yes = empty

        if state_str != last_state:
            ir_data = {"locker_empty": state_str}

            if state_str == "No":  # Parcel just placed
                ir_data["placed_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")  # ISO format
            else:
                # Optional: clear placed_at when locker is empty
                ir_data["placed_at"] = None

            with open(IR_STATE_FILE, 'w') as f:
                json.dump(ir_data, f)

            print(f"[IR] Locker {('Full' if state_str=='No' else 'Empty')}")
            last_state = state_str

        time.sleep(0.5)
