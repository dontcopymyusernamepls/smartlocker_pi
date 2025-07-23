import RPi.GPIO as GPIO
import time
import json

IR_SENSOR_PIN = 23
STATE_FILE = '/home/pi/shared/ir_status.json'

def setup():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(IR_SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def write_status(state):
    with open(STATE_FILE, 'w') as f:
        json.dump({"locker_empty": state}, f)

def loop():
    last_state = None
    while True:
        current_state = GPIO.input(IR_SENSOR_PIN)
        if current_state == 0 and last_state != "no":
            write_status("no")  # Parcel present
            last_state = "no"
        elif current_state == 1 and last_state != "yes":
            write_status("yes")  # Locker empty
            last_state = "yes"
        time.sleep(0.5)

def destroy():
    GPIO.cleanup()

if __name__ == '__main__':
    setup()
    try:
        loop()
    except KeyboardInterrupt:
        destroy()
