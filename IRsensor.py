def ir_sensor_loop():
    last_state = None
    while True:
        current_state = GPIO.input(IR_SENSOR_PIN)
        state_str = "No" if current_state == 0 else "Yes"  # No=full, Yes=empty

        # Load existing IR state data
        ir_data = {}
        if os.path.exists(IR_STATE_FILE):
            with open(IR_STATE_FILE, 'r') as f:
                try:
                    ir_data = json.load(f)
                except Exception:
                    ir_data = {}

        if state_str != last_state:
            # Save new state
            ir_data["locker_empty"] = state_str

            # Set or clear placed_at timestamp
            if state_str == "No":  # Locker just became full
                ir_data["placed_at"] = datetime.datetime.now().isoformat()
            elif state_str == "Yes":
                ir_data["placed_at"] = None

            # Write updated state
            with open(IR_STATE_FILE, 'w') as f:
                json.dump(ir_data, f)

            print(f"[IR] Locker {('Full' if state_str=='No' else 'Empty')}")
            last_state = state_str

        # Check if parcel has been in locker for >3 days
        if ir_data.get("locker_empty") == "No" and ir_data.get("placed_at"):
            try:
                placed_time = datetime.datetime.fromisoformat(ir_data["placed_at"])
                if (datetime.datetime.now() - placed_time).days > 3:
                    print("[ALERT] Parcel has been in locker for more than 3 days.")
            except Exception:
                pass

        time.sleep(0.5)
