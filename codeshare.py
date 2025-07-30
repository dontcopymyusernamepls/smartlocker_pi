def on_mqtt_message(client, userdata, msg):
    global current_pin
    if msg.topic == MQTT_TOPIC_PIN:
        try:
            data = json.loads(msg.payload)
            new_pin = data.get("pin", "").strip()  # Ensure we strip whitespace
            print(f"Received MQTT PIN update: {new_pin} (Current: {current_pin})")  # Debug
            if len(new_pin) == 6:
                current_pin = new_pin
                print(f"Updated PIN to: {current_pin}")
            else:
                print(f"Invalid PIN length: {new_pin}")
        except Exception as e:
            print(f"Error processing PIN update: {e}")

def commands():
    global input_code, failed_attempts, should_show_prompt
    secretCode = get_secret_code()
    print(f"Checking PIN: Input='{input_code.strip()}' vs Stored='{secretCode}'")  # Debug
    
    GPIO.output(C1, GPIO.HIGH)
    if GPIO.input(R2) == 1:  # C key
        input_code = ""
        lcd.lcd_clear()
        lcd.lcd_display_string("Cleared", 1, 5)
        sleep(1)
        lcd.lcd_clear()
        lcd.lcd_display_string("Enter your PIN:", 1, 0)
        should_show_prompt = False
        GPIO.output(C1, GPIO.LOW)
        return True

    if GPIO.input(R1) == 1:  # D key
        if input_code.strip() == secretCode.strip():  # Added strip() for comparison
            failed_attempts = 0
            lcd.lcd_clear()
            lcd.lcd_display_string("Correct!", 1, 4)
            GPIO.output(Relay, GPIO.LOW)
            GPIO.output(buzzer, GPIO.HIGH)
            sleep(0.3)
            GPIO.output(buzzer, GPIO.LOW)
            sleep(1)
            GPIO.output(Relay, GPIO.HIGH)
            mqtt_client.publish(MQTT_TOPIC_UNLOCK, "unlock")
            print("[MQTT] Unlock signal sent to Door_Pi")
        else:
            failed_attempts += 1
            print(f"Failed attempt {failed_attempts}. Input: '{input_code.strip()}', Expected: '{secretCode.strip()}'")  # Debug
            lcd.lcd_clear()
            lcd.lcd_display_string(f"{MAX_FAILED_ATTEMPTS - failed_attempts} attempts left", 1, 0)
            for _ in range(2):
                GPIO.output(buzzer, GPIO.HIGH)
                sleep(0.2)
                GPIO.output(buzzer, GPIO.LOW)
                sleep(0.2)

            if failed_attempts >= MAX_FAILED_ATTEMPTS:
                lcd.lcd_clear()
                lcd.lcd_display_string("LOCKED OUT!", 1, 0)
                GPIO.output(buzzer, GPIO.HIGH)
                sleep(5)
                GPIO.output(buzzer, GPIO.LOW)
                failed_attempts = 0

            sleep(1)
            lcd.lcd_clear()
            lcd.lcd_display_string("Enter your PIN:", 1, 0)

        input_code = ""
        should_show_prompt = False
        GPIO.output(C1, GPIO.LOW)
        return True
    GPIO.output(C1, GPIO.LOW)
    return False
