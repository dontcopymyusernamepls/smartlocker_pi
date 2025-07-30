import threading
import time
import json
import os
import board
import adafruit_dht
import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt
import I2C_LCD_driver
from time import sleep

# ========== Configuration ==========
MQTT_BROKER = "192.168.158.163"  # PI A's IP
MQTT_PORT = 1883

# Topics
MQTT_TOPIC_PIN = "locker/pin"
MQTT_TOPIC_SENSORS = "locker/sensors"
MQTT_TOPIC_UNLOCK = "locker/unlock"
MQTT_TOPIC_IR = "locker/ir"

# GPIO Configuration
IR_SENSOR_PIN = 23
C1, C2, C3, C4 = 5, 6, 13, 19
R1, R2, R3, R4 = 12, 16, 20, 21
buzzer = 26
Relay = 27

# Keypad variables
input_code = ""
failed_attempts = 0
MAX_FAILED_ATTEMPTS = 5
should_show_prompt = True
current_pin = "111111"  # Default PIN

# Initialize LCD
lcd = I2C_LCD_driver.lcd()
lcd.lcd_display_string("System loading", 1, 1)
for i in range(16):
    lcd.lcd_display_string(".", 2, i)
    sleep(0.1)
lcd.lcd_clear()

# GPIO Setup
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup([C1, C2, C3, C4], GPIO.OUT)
GPIO.setup([R1, R2, R3, R4], GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(buzzer, GPIO.OUT)
GPIO.setup(Relay, GPIO.OUT)
GPIO.setup(IR_SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.output(Relay, GPIO.HIGH)

# ========== MQTT Client ==========
def on_mqtt_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker")
    client.subscribe(MQTT_TOPIC_PIN)

def on_mqtt_message(client, userdata, msg):
    global current_pin
    if msg.topic == MQTT_TOPIC_PIN:
        try:
            data = json.loads(msg.payload)
            current_pin = data.get("pin", current_pin)
            print(f"Received new PIN: {current_pin}")
        except Exception as e:
            print(f"Error processing PIN update: {e}")

mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_mqtt_connect
mqtt_client.on_message = on_mqtt_message
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
mqtt_client.loop_start()

# ========== Sensor Functions ==========
def publish_sensor_data():
    dht_device = adafruit_dht.DHT11(board.D4)
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
                mqtt_client.publish(MQTT_TOPIC_SENSORS, json.dumps(data))
        except Exception as e:
            print(f"Sensor error: {e}")
        time.sleep(2)

def publish_ir_data():
    ALERT_THRESHOLD = 30  # 30 seconds for testing
    parcel_present_since = None
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
            message = "Parcel has not been collected for over threshold time"
        
        data = {
            "locker_empty": state_str,
            "message": message
        }
        
        mqtt_client.publish(MQTT_TOPIC_IR, json.dumps(data))
        time.sleep(0.5)

# ========== Keypad Functions ==========
def commands():
    global input_code, failed_attempts, should_show_prompt

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
        if input_code.strip() == current_pin:
            failed_attempts = 0
            lcd.lcd_clear()
            lcd.lcd_display_string("Correct!", 1, 4)
            GPIO.output(Relay, GPIO.LOW)
            GPIO.output(buzzer, GPIO.HIGH)
            sleep(0.3)
            GPIO.output(buzzer, GPIO.LOW)
            sleep(1)
            GPIO.output(Relay, GPIO.HIGH)
            
            # Send unlock command to PI C via MQTT
            mqtt_client.publish(MQTT_TOPIC_UNLOCK, "unlock")
            print("[MQTT] Unlock signal sent to Door_Pi")
                
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

# ========== Main Execution ==========
if __name__ == '__main__':
    try:
        # Start sensor threads
        threading.Thread(target=publish_sensor_data, daemon=True).start()
        threading.Thread(target=publish_ir_data, daemon=True).start()

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
