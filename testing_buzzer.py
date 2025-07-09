import RPi.GPIO as GPIO
from time import sleep

buzzer = 17 

GPIO.setmode(GPIO.BCM)
GPIO.setup(buzzer, GPIO.OUT)

try:
	GPIO.output(buzzer, GPIO.HIGH)
	print("Buzzer on for 2 seconds")
	sleep(2)
	GPIO.output(buzzer, GPIO.LOW)
	print("Buzzer off")

finally:
	GPIO.cleanup()
