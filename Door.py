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

	print("Monitoring if door remains closed for too long...")
	start_time = time()

	while DOOR_CLOSED:
		elapsed = time() - start_time
		if elapsed > MAX_DOOR_CLOSE_TIME:
			print("ALERT: Door has remained closed too long!")
			try:
				response = requests.post(
					'http://10.189.197.148:5000/door-alert',
					json={"alert": "Parcel has not been collected for more than 3 days.", "timestamp": time()}
		        )
				print("Alert sent to admin dashboard:", response.status_code)
			except Exception as e:
				print("Failed to send alert:", e)
			break
		sleep

except Exception as e:
	print(f"Error occurred: {e}")

finally:
	servo.mid()
	sleep(1)
	print("Script finished cleanly.")
