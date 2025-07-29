import threading
import time
import json
import os
import board
import adafruit_dht
import RPi.GPIO as GPIO
import requests
from flask import Flask, request, jsonify
import I2C_LCD_driver
from time import sleep

# ===========================================================
# ========== GLOBAL CONFIGURATION ===========================
# ===========================================================
SENSOR_DATA_FILE = '/home/smartlocker/stats/sensor_data.json'
IR_STATE_FILE = '/home/smartlocker/stats/ir_sensor.json'

# GPIO for IR Sensor
IR_SENSOR_PIN = 23

# DHT11 sensor
dht_device = adafruit_dht.DHT11(board.D4)

# Keypad & Smartlock
C1, C2, C3, C4 = 5, 6, 13, 19
R1, R2, R3, R4 = 12, 16, 20, 21
buzzer = 26
Relay = 27
relayState = True
input_code = ""
failed_attempts = 0
MAX_FAILED_ATTEMPTS = 5
should_show_prompt = True

lcd = I2C_LCD_driver.lcd()
lcd.lcd_display_string("System loading", 1, 1)
for i in range(16):
    lcd.lcd_display_string(".", 2, i)
    sleep(0.1)
lcd.lcd_clear()

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup([C1, C2, C3, C4], GPIO.OUT)
GPIO.setup([R1, R2, R3, R4], GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(buzzer, GPIO.OUT)
GPIO.setup(Relay, GPIO.OUT)
GPIO.setup(IR_SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.output(Relay, GPIO.HIGH)

# ===========================================================
# ========== FLASK SERVER ===================================
# ===========================================================
app = Flask(__name__)
shared_data = {'pin': '111111'}

@app.route('/set-pin', methods=['POST'])
def set_pin():
    data = request.get_json()
    new_pin = data.get('pin')
    if new_pin and len(new_pin) == 6:
        shared_data['pin'] = new_pin
        return {'status': 'success', 'pin': new_pin}
    return {'status': 'error', 'message': 'Invalid pin'}, 400

@app.route('/get-pin', methods=['GET'])
def get_pin():
    return {'pin': shared_data['pin']}

@app.route('/locker-statistics', methods=['GET'])
def locker_statistics():
    try:
        # Read DHT data
        if not os.path.exists(SENSOR_DATA_FILE):
            return jsonify({"status": "error", "message": "Sensor data not available"}), 404
        with open(SENSOR_DATA_FILE, 'r') as f:
            sensor_data = json.load(f)

        # Read IR data
        locker_empty = "-"
        if os.path.exists(IR_STATE_FILE):
            with open(IR_STATE_FILE, 'r') as f_ir:
                ir_data = json.load(f_ir)
            locker_empty = ir_data.get("locker_empty", "-")

        return jsonify({
            "status": "success",
            "temperature": sensor_data.get("temperature"),
            "humidity": sensor_data.get("humidity"),
            "timestamp": sensor_data.get("timestamp"),
            "locker_empty": locker_empty
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ===========================================================
# ========== IR SENSOR THREAD ===============================
# ===========================================================
def ir_sensor_loop():
    last_state = None
    while True:
        current_state = GPIO.input(IR_SENSOR_PIN)
        state_str = "No" if current_state == 0 else "Yes"  # No=full, Yes=empty
        if state_str != last_state:
            with open(IR_STATE_FILE, 'w') as f:
                json.dump({"locker_empty": state_str}, f)
            print(f"[IR] Locker {('Full' if state_str=='No' else 'Empty')}")
            last_state = state_str
        time.sleep(0.5)

# ===========================================================
# ========== DHT SENSOR THREAD ==============================
# ===========================================================
def dht_sensor_loop():
    while True:
        try:
            temperature = dht_device.temperature
            humidity = dht_device.humidity
            if temperature is not None and humidity is not None:
                data = {
                    "temperature": temperature,
                    "humidity": humidity,
                    "timestamp": time.time()
                }
                with open(SENSOR_DATA_FILE, 'w') as f:
                    json.dump(data, f)
                print(f"[DHT] Temp={temperature:.1f}C Humidity={humidity:.1f}%")
        except Exception as e:
            print("[DHT] Reading failed:", e)
        time.sleep(2)

# ===========================================================
# ========== SMARTLOCK KEYPAD ===============================
# ===========================================================
def get_secret_code():
    try:
        r = requests.get("http://10.189.197.16:5000/get-pin", timeout=2)
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
    global input_code, relayState, failed_attempts, should_show_prompt
    secretCode = get_secret_code()

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

        input_code = ""
        should_show_prompt = False
        GPIO.output(C1, GPIO.LOW)
        return True
    GPIO.output(C1, GPIO.LOW)
    return False

def read(column, chars):
    global input_code
    GPIO.output(column, GPIO.HIGH)
    row_states = [GPIO.input(R1), GPIO.input(R2), GPIO.input(R3), GPIO.input(R4)]
    for idx, state in enumerate(row_states):
        if state == 1:
            key = chars[idx]
            if key not in ['C', 'D']:
                if len(input_code) < 6:
                    input_code += key
                    lcd.lcd_display_string(input_code.strip(), 2, 0)
                    print(f"[KEYPAD] {input_code}")
    GPIO.output(column, GPIO.LOW)

# ===========================================================
# ========== MAIN EXECUTION =================================
# ===========================================================
if __name__ == '__main__':
    try:
        # Start sensor threads
        threading.Thread(target=ir_sensor_loop, daemon=True).start()
        threading.Thread(target=dht_sensor_loop, daemon=True).start()

        # Start Flask server in a thread
        threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000), daemon=True).start()

        # Smartlock main loop
        while True:
            if should_show_prompt:
                lcd.lcd_clear()
                lcd.lcd_display_string("Enter your PIN:", 1, 0)
                should_show_prompt = False

            if not commands():
                read(C1, ["D", "C", "B", "A"])
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
