if input_code.strip() == secretCode:
    failed_attempts = 0
    lcd.lcd_clear()
    lcd.lcd_display_string("Correct!", 1, 4)
    GPIO.output(Relay, GPIO.LOW)
    GPIO.output(buzzer, GPIO.HIGH)
    sleep(0.3)
    GPIO.output(buzzer, GPIO.LOW)
    sleep(1)
    GPIO.output(Relay, GPIO.HIGH)

    # --- MQTT unlock signal added here ---
    try:
        publish.single("locker/unlock", payload="unlock", hostname="10.189.197.148")
        print("[MQTT] Unlock signal sent to .148 Pi")
    except Exception as e:
        print("[MQTT] Failed to send unlock signal:", e)
