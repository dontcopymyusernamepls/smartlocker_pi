import RPi.GPIO as GPIO
import time

ObstaclePin = 23  # GPIO pin number

def setup():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(ObstaclePin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def loop():
    last_state = None  # Track last state to avoid spamming output

    while True:
        current_state = GPIO.input(ObstaclePin)
        
        if current_state == 0:  # Obstacle detected
            if last_state != "present":
                print("Parcel present")
                last_state = "present"
        else:  # No obstacle
            if last_state != "absent":
                print("Locker empty")
                last_state = "absent"

        time.sleep(0.5)  # Adjust polling rate as needed

def destroy():
    GPIO.cleanup()

if __name__ == '__main__':
    setup()
    try:
        loop()
    except KeyboardInterrupt:
        destroy()
