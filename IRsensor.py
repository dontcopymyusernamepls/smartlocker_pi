def ir_sensor_loop():
    global parcel_present_since
    last_state = None
    while True:
        current_state = GPIO.input(IR_SENSOR_PIN)
        state_str = "No" if current_state == 0 else "Yes"
        
        # Track parcel presence
        if state_str == "No" and parcel_present_since is None:
            parcel_present_since = time.time()
        elif state_str == "Yes":
            parcel_present_since = None
        
        # Check if parcel has been there too long
        message = None
        if (parcel_present_since is not None and 
            (time.time() - parcel_present_since) > ALERT_THRESHOLD):
            message = "Parcel has been in locker for over 3 days"
            print(f"[ALERT] {message}")
        
        # Always write both fields
        data = {
            "locker_empty": state_str,
            "message": message if message else None  # Explicit None instead of empty string
        }
        
        with open(IR_STATE_FILE, 'w') as f:
            json.dump(data, f)
        
        last_state = state_str
        time.sleep(0.5)
