import time
import board
import adafruit_dht

# Create the sensor instance on GPIO 4 (D4)
dht_device = adafruit_dht.DHT11(board.D4)

while True:
    try:
        # Try to read temperature and humidity
        temperature = dht_device.temperature
        humidity = dht_device.humidity

        if humidity is not None and temperature is not None:
            print("Temp={0:0.1f}C Humidity={1:0.1f}%".format(temperature, humidity))
        else:
            print("Sensor failure. Check wiring.")

    except Exception as e:
        print("Reading failed:", e)

    time.sleep(2)
