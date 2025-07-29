# Keypad input function
def commands():
    global correct_pin
    password = ""
    display_default()

    while True:
        for j in range(3):
            GPIO.output(COL[j], 0)
            for i in range(4):
                if GPIO.input(ROW[i]) == 0:
                    key = Matrix[i][j]
                    if key == "#":
                        print("Entered PIN:", password)
                        if password == str(correct_pin):
                            print("[PIN] Correct PIN entered")

                            # Feedback
                            GPIO.output(Relay, GPIO.LOW)
                            GPIO.output(buzzer, GPIO.HIGH)
                            sleep(0.3)
                            GPIO.output(buzzer, GPIO.LOW)
                            sleep(1)
                            GPIO.output(Relay, GPIO.HIGH)

                            # ✅ Send MQTT unlock message
                            try:
                                publish.single("locker/unlock", payload="unlock", hostname="10.189.197.148")
                                print("[MQTT] Unlock signal sent to .148 Pi")
                            except Exception as e:
                                print("[MQTT] Failed to send unlock signal:", e)

                            lcd.lcd_clear()
                            lcd.lcd_display_string("Access Granted", 1)
                            lcd.lcd_display_string("Door Opened", 2)
                        else:
                            print("[PIN] Incorrect PIN")
                            lcd.lcd_clear()
                            lcd.lcd_display_string("Access Denied", 1)
                            lcd.lcd_display_string("Try Again", 2)
                            GPIO.output(buzzer, GPIO.HIGH)
                            sleep(1)
                            GPIO.output(buzzer, GPIO.LOW)
                        sleep(2)
                        password = ""
                        display_default()

                    elif key == "*":
                        password = ""
                        lcd.lcd_clear()
                        display_default()
                    else:
                        password += str(key)
                        lcd.lcd_clear()
                        lcd.lcd_display_string("PIN: " + "*"*len(password), 2)
                    while GPIO.input(ROW[i]) == 0:
                        pass
            GPIO.output(COL[j], 1)
        sleep(0.1)
