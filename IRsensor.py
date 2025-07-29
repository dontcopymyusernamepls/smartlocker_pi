def ir_sensor_loop():
    global parcel_present_since
    last_state = None
    while True:
        current_state = GPIO.input(IR_SENSOR_PIN)
        state_str = "No" if current_state == 0 else "Yes"  # No=full, Yes=empty
        
        # Track when parcel was first detected
        if state_str == "No" and parcel_present_since is None:
            parcel_present_since = time.time()
            print(f"[IR] Parcel detected at {parcel_present_since}")
        elif state_str == "Yes":
            parcel_present_since = None
        
        # Check if parcel has been there too long
        if (parcel_present_since is not None and 
            (time.time() - parcel_present_since) > ALERT_THRESHOLD):
            print("[ALERT] Parcel has been in locker too long!")
            
            # Send HTTP request to your Flutter app
            try:
                requests.post(
                    "http://<YOUR_PHONE_IP>:<PORT>/alert",
                    json={
                        "message": "Parcel has been in locker for over 3 days",
                        "timestamp": time.time()
                    },
                    timeout=2
                )
            except Exception as e:
                print(f"Failed to send alert to phone: {e}")
            
            # Reset timer to avoid spamming alerts
            parcel_present_since = time.time() - (ALERT_THRESHOLD - 10)  # Give 10 sec buffer
            
        if state_str != last_state:
            with open(IR_STATE_FILE, 'w') as f:
                json.dump({
                    "locker_empty": state_str,
                    "parcel_present_since": parcel_present_since
                }, f)
            print(f"[IR] Locker {('Full' if state_str=='No' else 'Empty')}")
            last_state = state_str
        time.sleep(0.5)
