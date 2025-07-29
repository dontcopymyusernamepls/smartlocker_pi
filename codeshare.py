from flask import Flask, jsonify
import Adafruit_DHT
import RPi.GPIO as GPIO
import I2C_LCD_driver
from pad4pi import rpi_gpio
import paho.mqtt.client as mqtt
from time import sleep
from datetime import datetime
import random

# === GPIO SETUP ===
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

Relay = 20
IR = 16
buzzer = 26

GPIO.setup(Relay, GPIO.OUT)
GPIO.setup(IR, GPIO.IN)
GPIO.setup(buzzer, GPIO.OUT)

GPIO.output(Relay, GPIO.HIGH)
GPIO.output(buzzer, GPIO.LOW)

# === LCD Setup ===
lcd = I2C_LCD_driver.lcd()

# === MQTT Setup ===
MQTT_BROKER = "192.168.1.148"  # IP of .148 Pi
MQTT_PORT = 1883
MQTT_TOPIC = "locker/open"

def send_mqtt_open():
    try:
        client = mqtt.Client()
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.publish(MQTT_TOPIC, "open")
        client.disconnect()
        print("[MQTT] Published 'open' to locker/open")
    except Exception as e:
        print(f"[MQTT] Error: {e}")

# === Flask Setup ===
app = Flask(__name__)
latest_otp = {'otp': None}

@app.route('/set_otp/<code>', methods=['GET'])
def set_otp(code):
    latest_otp['otp'] = code
    print(f"[Flask] OTP set to: {code}")
    return jsonify({"status": "success", "otp": code})

@app.route('/stats', methods=['GET'])
def get_stats():
    humidity, temperature = Adafruit_DHT.read_retry(Adafruit_DHT.DHT11, 4)
    presence = GPIO.input(IR)
    return jsonify({
        "temperature": temperature,
        "humidity": humidity,
        "presence": bool(not presence),  # 0 when detected
    })

# === Keypad Setup ===
KEYPAD = [
    ["1", "2", "3", "A"],
    ["4", "5", "6", "B"],
    ["7", "8", "9", "C"],
    ["*", "0", "#", "D"]
]

ROW_PINS = [5, 6, 13, 19]
COL_PINS = [12, 17, 27, 22]

factory = rpi_gpio.KeypadFactory()
keypad = factory.create_keypad(keypad=KEYPAD, row_pins=ROW_PINS, col_pins=COL_PINS)

# === Secret Code Management ===
def get_secret_code():
    return latest_otp['otp']

# === Keypad Input Handling ===
user_input = ""

def commands(key):
    global user_input
    if key == "#":
        print(f"[Keypad] Entered PIN: {user_input}")
        if user_input == get_secret_code():
            lcd.clear()
            lcd.lcd_display_string("Access Granted", 1)
            print("[System] Correct PIN")
            send_mqtt_open()  # Notify .148 Pi to open the locker
            GPIO.output(buzzer, GPIO.HIGH)
            sleep(0.3)
            GPIO.output(buzzer, GPIO.LOW)
        else:
            lcd.clear()
            lcd.lcd_display_string("Access Denied", 1)
            print("[System] Wrong PIN")
            for _ in range(3):
                GPIO.output(buzzer, GPIO.HIGH)
                sleep(0.2)
                GPIO.output(buzzer, GPIO.LOW)
                sleep(0.2)
        user_input = ""
        lcd.lcd_display_string("Enter PIN:", 1)
    elif key == "*":
        user_input = ""
        lcd.clear()
        lcd.lcd_display_string("Enter PIN:", 1)
        print("[Keypad] Input cleared")
    else:
        user_input += key
        lcd.lcd_display_string("*" * len(user_input), 2)

keypad.registerKeyPressHandler(commands)

# === Start Flask and LCD ===
if __name__ == '__main__':
    lcd.lcd_display_string("Locker Ready", 1)
    lcd.lcd_display_string("Enter PIN:", 2)
    app.run(host='0.0.0.0', port=5000)
