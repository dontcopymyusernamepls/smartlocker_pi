import I2C_LCD_driver
import RPi.GPIO as GPIO
from time import sleep
import requests

# === GPIO PIN SETUP ===
C1, C2, C3, C4 = 5, 6, 13, 19
R1, R2, R3, R4 = 12, 16, 20, 21
buzzer = 17
Relay = 27
relayState = True

# === STATE TRACKING ===
input = ""
failed_attempts = 0
MAX_FAILED_ATTEMPTS = 5
should_show_prompt = True

# === LCD ===
lcd = I2C_LCD_driver.lcd()
lcd.lcd_display_string("System loading", 1, 1)
for i in range(16):
    lcd.lcd_display_string(".", 2, i)
    sleep(0.1)
lcd.lcd_clear()

# === GPIO INIT ===
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup([C1, C2, C3, C4], GPIO.OUT)
GPIO.setup([R1, R2, R3, R4], GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(buzzer, GPIO.OUT)
GPIO.setup(Relay, GPIO.OUT)
GPIO.output(Relay, GPIO.HIGH)

def get_secret_code():
    try:
        r = requests.get("http://192.168.1.14:5000/get-pin", timeout=2)
        if r.status_code == 200:
            return r.json().get("pin", "000000")
    except Exception as e:
        print(f"[!] Failed to get code: {e}")
    return "000000"

def setAllCols(state):
    GPIO.output(C1, state)
    GPIO.output(C2, state)
    GPIO.output(C3, state)
    GPIO.output(C4, state)

def commands():
    global input, relayState, failed_attempts, should_show_prompt

    secretCode = get_secret_code()

    # Scan column C1 for Clear (C) and Enter (D) keys
    GPIO.output(C1, GPIO.HIGH)
    if GPIO.input(R2) == 1:  # C key (Clear)
        input = ""
        lcd.lcd_clear()
        lcd.lcd_display_string("Cleared", 1, 5)
        sleep(1)
        lcd.lcd_clear()
        lcd.lcd_display_string("Enter your PIN:", 1, 0)
        should_show_prompt = False
        GPIO.output(C1, GPIO.LOW)
        return True

    if GPIO.input(R1) == 1:  # D key (Enter)
        if input.strip() == secretCode:
            failed_attempts = 0
            lcd.lcd_clear()
            lcd.lcd_display_string("Correct!", 1, 4)
            GPIO.output(Relay, GPIO.LOW)
            GPIO.output(buzzer, GPIO.HIGH)
            sleep(0.3)
            GPIO.output(buzzer, GPIO.LOW)
            sleep(1)
            GPIO.output(Relay, GPIO.HIGH)
        else:
            failed_attempts += 1
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

        input = ""
        should_show_prompt = False
        GPIO.output(C1, GPIO.LOW)
        return True

    GPIO.output(C1, GPIO.LOW)

    return False


def read(column, chars):
    global input
    GPIO.output(column, GPIO.HIGH)
    row_states = [GPIO.input(R1), GPIO.input(R2), GPIO.input(R3), GPIO.input(R4)]
    for idx, state in enumerate(row_states):
        if state == 1:
            key = chars[idx]
            # Don't add Clear 'C' or Enter 'D' keys to input
            if key not in ['C', 'D']:
                # Limit input length to max 6 characters (adjust as needed)
                if len(input) < 6:
                    input += key
                    lcd.lcd_display_string(input.strip(), 2, 0)
                    print(f"[KEYPAD] {input}")
    GPIO.output(column, GPIO.LOW)

try:
    while True:
        if should_show_prompt:
            lcd.lcd_clear()
            lcd.lcd_display_string("Enter your PIN:", 1, 0)
            should_show_prompt = False

        if not commands():
            read(C1, ["D", "C", "B", "A"])  # D=Enter, C=Clear
            read(C2, ["#", "9", "6", "3"])
            read(C3, ["0", "8", "5", "2"])
            read(C4, ["*", "7", "4", "1"])
            sleep(0.2)
        else:
            sleep(0.2)

except KeyboardInterrupt:
    print("[!] Stopped.")
finally:
    GPIO.cleanup()
