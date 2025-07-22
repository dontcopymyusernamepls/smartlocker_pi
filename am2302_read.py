import adafruit_dht
import board
import time

dht_device = adafruit_dht.DHT22(board.D4)  # or D17 if you change pin
time.sleep(2)  # Wait before first reading

try:
    temperature = dht_device.temperature
    humidity = dht_device.humidity

    if humidity is not None and temperature is not None:
        print("Temperature: {:.1f}C".format(temperature))
        print("Humidity: {:.1f}%".format(humidity))
    else:
        print("Failed to retrieve data from sensor")
except RuntimeError as error:
    print(f"Reading from DHT22 failed: {error}")




