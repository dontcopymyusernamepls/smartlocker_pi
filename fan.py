from gpiozero import Servo
from gpiozero.pins.pigpio import PiGPIOFactory
# Servo Motor (Fan simulation) setup
SERVO_PIN = 17  # Change this to your actual GPIO pin
factory = PiGPIOFactory()
servo = Servo(SERVO_PIN, pin_factory=factory)
FAN_THRESHOLD = 28  # Temperature threshold in Celsius
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
                
                # Control servo based on temperature
                if temperature > FAN_THRESHOLD:
                    servo.max()  # Spin the servo (simulate fan on)
                    print("[FAN] Temperature high - activating servo (fan)")
                else:
                    servo.min()  # Stop the servo (simulate fan off)
                    print("[FAN] Temperature normal - deactivating servo (fan)")
                    
        except Exception as e:
            print("[DHT] Reading failed:", e)
        time.sleep(2)

  finally:
    servo.close()  # Properly cleanup servo resources
    GPIO.cleanup()
