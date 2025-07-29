import RPi.GPIO as GPIO
import time
import json

IR_SENSOR_PIN = 23
STATE_FILE = '/home/smartlocker/stats/ir_sensor.json'

def setup():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(IR_SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def write_status(state):
    status_data = {"locker_empty": state}
    
    if state == "No":  # Parcel inserted
        status_data["placed_at"] = datetime.datetime.now().isoformat()
    elif state == "Yes":  # Parcel removed
        status_data["placed_at"] = None

    with open(STATE_FILE, 'w') as f:
        json.dump(status_data, f)

def loop():
    last_state = None
    while True:
        current_state = GPIO.input(IR_SENSOR_PIN)
        if current_state == 0 and last_state != "No":
            write_status("No")  # Parcel present
            print("Locker Full")
            last_state = "No"
        elif current_state == 1 and last_state != "Yes":
            write_status("Yes")  # Locker empty
            print("Locker Empty")
            last_state = "Yes"
        time.sleep(0.5)

def destroy():
    GPIO.cleanup()

if __name__ == '__main__':
    setup()
    try:
        loop()
    except KeyboardInterrupt:
        destroy()
