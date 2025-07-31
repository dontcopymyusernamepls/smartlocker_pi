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
import tempfile
import shutil
from gpiozero import Servo
from gpiozero.pins.pigpio import PiGPIOFactory

# ===========================================================
# ========== GLOBAL CONFIGURATION ===========================
# ===========================================================
SENSOR_DATA_FILE = '/home/smartlocker/stats/sensor_data.json'
IR_STATE_FILE = '/home/smartlocker/stats/ir_sensor.json'

# MQTT Configuration
MQTT_BROKER = "192.168.158.163"  # PI A's IP
MQTT_PORT = 1883
MQTT_TOPIC_PIN = "locker/pin"
MQTT_TOPIC_SENSORS = "locker/sensors"
MQTT_TOPIC_UNLOCK = "locker/unlock"
MQTT_TOPIC_IR = "locker/ir"
MQTT_TOPIC_DOOR_STATUS = "locker/door_status"  # Added for door status messages

# GPIO for IR Sensor
IR_SENSOR_PIN = 23

# DHT11 sensor
dht_device = adafruit_dht.DHT11(board.D4)

# Servo Motor (Fan simulation)
SERVO_PIN = 17 
factory = PiGPIOFactory()
servo = Servo(SERVO_PIN, pin_factory=factory)
GPIO.setup(SERVO_PIN, GPIO.OUT)
servo_pwm = GPIO.PWM(SERVO_PIN, 50)
servo_pwm.start(0)
FAN_THRESHOLD = 28  # Temperature threshold in Celsius

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
current_pin = "111111"  # Default PIN

# LCD Setup
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

# =================== SAFE WRITING CONFIGS ==========================
def safe_write_json(data, path):
    with tempfile.NamedTemporaryFile('w', delete=False) as tmp:
        json.dump(data, tmp)
        temp_path = tmp.name
    shutil.move(temp_path, path)

# ===========================================================
# ========== LCD DISPLAY FUNCTIONS =========================
# ===========================================================
def show_default_screen():
    """Show the default PIN entry screen"""
    lcd.lcd_clear()
    lcd.lcd_display_string("Enter your PIN:", 1, 0)
    if input_code:
        lcd.lcd_display_string("*" * len(input_code), 2, 0)

def show_door_status(action, status, extra_data=None):
    """Display door status messages on LCD"""
    lcd.lcd_clear()
    
    if action == "opening":
        lcd.lcd_display_string("Door Opening...", 1)
    elif action == "opened":
        lcd.lcd_display_string("Door Unlocked", 1)
        if extra_data and 'remaining' in extra_data:
            lcd.lcd_display_string(f"Closes in: {extra_data['remaining']}s", 2)
    elif action == "closing":
        lcd.lcd_display_string("Door Closing...", 1)
    elif action == "closed":
        lcd.lcd_clear()
        lcd.lcd_display_string("Door Locked", 1)
        sleep(2)  # Show message for 2 seconds
        show_default_screen()
    elif action == "error":
        lcd.lcd_display_string("ERROR:", 1)
        if extra_data and 'message' in extra_data:
            error_msg = extra_data['message'][:16]  # Truncate to fit LCD
            lcd.lcd_display_string(error_msg, 2)
        sleep(3)  # Show error for 3 seconds
        show_default_screen()
    elif action == "system":
        if status == "online":
            lcd.lcd_display_string("System Online", 1)
        elif status == "offline":
            lcd.lcd_display_string("System Offline", 1)
        sleep(1.5)
        show_default_screen()

# ===========================================================
# ========== MQTT CLIENT ====================================
# ===========================================================
def on_mqtt_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker")
    client.subscribe(MQTT_TOPIC_PIN)
    client.subscribe(MQTT_TOPIC_DOOR_STATUS)  # Subscribe to door status updates

def on_mqtt_message(client, userdata, msg):
    global current_pin
    try:
        if msg.topic == MQTT_TOPIC_PIN:
            try:
                data = json.loads(msg.payload)
                new_pin = data.get("pin", "").strip()
                print(f"Received MQTT PIN update: {new_pin} (Current: {current_pin})")
                if len(new_pin) == 6:
                    current_pin = new_pin
                    print(f"Updated PIN to: {current_pin}")
                    # Show confirmation on LCD
                    lcd.lcd_clear()
                    lcd.lcd_display_string("PIN Updated", 1, 3)
                    sleep(1.5)
                    show_default_screen()
                else:
                    print(f"Invalid PIN length: {new_pin}")
            except Exception as e:
                print(f"Error processing PIN update: {e}")
                
        elif msg.topic == MQTT_TOPIC_DOOR_STATUS:
            try:
                data = json.loads(msg.payload)
                action = data.get("action")
                status = data.get("status")
                show_door_status(action, status, data)
            except Exception as e:
                print(f"Error processing door status: {e}")
                
    except Exception as e:
        print(f"MQTT message processing error: {e}")

mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_mqtt_connect
mqtt_client.on_message = on_mqtt_message
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
mqtt_client.loop_start()

# ===========================================================
# ========== IR SENSOR THREAD ===============================
# ===========================================================
ALERT_THRESHOLD = 30  # 30 seconds for testing (change to 259200 for 3 days in production)
parcel_present_since = None

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
            message = "Parcel has not been collected for over 3 days"
            print(f"[ALERT] {message}")
            # Show alert on LCD
            lcd.lcd_clear()
            lcd.lcd_display_string("Parcel Alert!", 1, 2)
            lcd.lcd_display_string("Collect ASAP", 2, 2)
            sleep(3)
            show_default_screen()
        
        # Always write both fields
        data = {
            "locker_empty": state_str,
            "message": message if message else None
        }
        print(f"[DEBUG] Writing IR Data: {data}")
        
        safe_write_json(data, IR_STATE_FILE)
        mqtt_client.publish(MQTT_TOPIC_IR, json.dumps(data))
        
        last_state = state_str
        time.sleep(0.5)

# ===========================================================
# ========== DHT SENSOR THREAD ==============================
# ===========================================================
def oscillate_servo():
    for _ in range(5):
        servo.max() #90
        time.sleep(0.15)
        servo.min() #90
        time.sleep(0.15)
    servo.detach()  # Stop
    
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
                safe_write_json(data, SENSOR_DATA_FILE)
                mqtt_client.publish(MQTT_TOPIC_SENSORS, json.dumps(data))
                print(f"[DHT] Temp={temperature:.1f}C Humidity={humidity:.1f}%")
                
                # Show temp/humidity on LCD if no other activity
                if not input_code:
                    lcd.lcd_clear()
                    lcd.lcd_display_string(f"Temp: {temperature:.1f}C", 1)
                    lcd.lcd_display_string(f"Hum: {humidity:.1f}%", 2)
                    sleep(3)
                    show_default_screen()
                
                # Control servo based on temperature
                if temperature > FAN_THRESHOLD:
                    print("[FAN] Temperature high - activating servo")
                    oscillate_servo()
                else:
                    servo.detach()
                    
        except Exception as e:
            print("[DHT] Reading failed:", e)
        time.sleep(2)

# ===========================================================
# ========== SMARTLOCK KEYPAD ===============================
# ===========================================================
def get_secret_code():
    return current_pin

def setAllCols(state):
    GPIO.output(C1, state)
    GPIO.output(C2, state)
    GPIO.output(C3, state)
    GPIO.output(C4, state)

def commands():
    global input_code, failed_attempts, should_show_prompt
    secretCode = get_secret_code()
    print(f"Checking PIN: Input='{input_code.strip()}' vs Stored='{secretCode}'")
    
    GPIO.output(C1, GPIO.HIGH)
    if GPIO.input(R2) == 1:  # C key
        input_code = ""
        lcd.lcd_clear()
        lcd.lcd_display_string("Cleared", 1, 5)
        sleep(1)
        show_default_screen()
        should_show_prompt = False
        GPIO.output(C1, GPIO.LOW)
        return True

    if GPIO.input(R1) == 1:  # D key
        if input_code.strip() == secretCode.strip():
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
            print(f"Failed attempt {failed_attempts}. Input: '{input_code.strip()}', Expected: '{secretCode.strip()}'")
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
            show_default_screen()

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
                    lcd.lcd_display_string("*" * len(input_code), 2, 0)  # Show asterisks instead of numbers
                    print(f"[KEYPAD] {input_code}")
    GPIO.output(column, GPIO.LOW)

# ===========================================================
# ========== MAIN EXECUTION =================================
# ===========================================================
if __name__ == '__main__':
    try:
        # Initialize with default screen
        show_default_screen()
        
        # Start sensor threads
        threading.Thread(target=ir_sensor_loop, daemon=True).start()
        threading.Thread(target=dht_sensor_loop, daemon=True).start()

        # Smartlock main loop
        while True:
            if should_show_prompt:
                show_default_screen()
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
        servo_pwm.stop()
        GPIO.cleanup()
        lcd.lcd_clear()
