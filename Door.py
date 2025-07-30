from gpiozero import Servo
from gpiozero.pins.pigpio import PiGPIOFactory
from time import sleep, time
import requests
		

# Setup sevo on GPIO17 using pigpio
factory =  PiGPIOFactory()
servo = Servo(17, pin_factory=factory)

WAIT_TIME = 10
MAX_DOOR_CLOSE_TIME = 30

DOOR_CLOSED = True

try:
	print("Starting Smart Door Sequence...")
	
	print("Unlocking the locker")
	servo.max()
	sleep(1)
	
	print(f"Door will stay unlocked for 30 seconds...")
	sleep(30)

	print("Locking the locker")
	servo.min()
	sleep(2.5)

	print("Returning servo to center (rest)...")
	servo.mid()
	sleep(1)


except Exception as e:
	print(f"Error occurred: {e}")

finally:
	servo.mid()
	sleep(1)
	print("Script finished cleanly.")
