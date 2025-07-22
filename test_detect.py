import RPi.GPIO as GPIO
from time import sleep

GPIO.setmode(GPIO.BCM)
sensor_pin = 26
GPIO.setup(sensor_pin, GPIO.IN)

try:
    while True:
        if GPIO.input(sensor_pin) == GPIO.LOW:
            print("🔴 Blocked (parcel present)")
        else:
            print("🟢 Clear (no parcel)")
        sleep(0.5)
except KeyboardInterrupt:
    GPIO.cleanup()
