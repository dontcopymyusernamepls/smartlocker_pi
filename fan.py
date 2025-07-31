from gpiozero import Servo
from gpiozero.pins.pigpio import PiGPIOFactory
# Servo Motor (Fan simulation) setup
SERVO_PIN = 17  # Change this to your actual GPIO pin
factory = PiGPIOFactory()
servo = Servo(SERVO_PIN, pin_factory=factory)
FAN_THRESHOLD = 28  # Temperature threshold in Celsius



servo_pwm = GPIO.PWM(SERVO_PIN, 50)
servo_pwm.start(0)

# Add the oscillation function
def oscillate_servo():
    for _ in range(5):
        servo_pwm.ChangeDutyCycle(7.5)  # 90°
        time.sleep(0.15)
        servo_pwm.ChangeDutyCycle(2.5)  # -90°
        time.sleep(0.15)
    servo_pwm.ChangeDutyCycle(0)  # Stop

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
                
                # Servo control logic
                if temperature > FAN_THRESHOLD:
                    print("[FAN] Temperature high - activating servo")
                    oscillate_servo()  # Call the oscillation function
                else:
                    servo_pwm.ChangeDutyCycle(0)  # Stop servo
                    
        except Exception as e:
            print("[DHT] Reading failed:", e)
        time.sleep(2)


finally:
    servo_pwm.stop()
    GPIO.cleanup()
