import RPi.GPIO as GPIO
import time
import json

ObstaclePin = 23  # GPIO pin number
status_file = "/home/smartlocker/stats/ir_status.json"

def setup():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(ObstaclePin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def save_status(is_present):
    # Write presence status to JSON file
    with open(status_file, "w") as f:
        json.dump({"parcel_present": is_present}, f)

def loop():
    last_state = None

    while True:
        current_state = GPIO.input(ObstaclePin)
        # current_state == 0 means obstacle detected (parcel present)
        is_present = (current_state == 0)

        if last_state != is_present:
            if is_present:
                print("Parcel present")
            else:
                print("Locker empty")
            save_status(is_present)
            last_state = is_present

        time.sleep(0.5)

def destroy():
    GPIO.cleanup()

if __name__ == '__main__':
    setup()
    try:
        loop()
    except KeyboardInterrupt:
        destroy()
