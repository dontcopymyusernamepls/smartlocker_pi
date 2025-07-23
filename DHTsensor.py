import time
import board
import adafruit_dht
import json

# Initialize DHT11 sensor on GPIO 4 (D4)
dht_device = adafruit_dht.DHT11(board.D4)

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
            with open('/home/pi/sensor_data.json', 'w') as f:
                json.dump(data, f)

            print(f"Temp={temperature:.1f}C Humidity={humidity:.1f}%")
        else:
            print("Sensor failure. Check wiring.")

    except Exception as e:
        print("Reading failed:", e)

    time.sleep(2)
