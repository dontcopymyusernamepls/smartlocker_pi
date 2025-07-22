import RPi.GPIO as GPIO
import time

class DHT22Result:
    ERR_NO_ERROR = 0
    ERR_TIMEOUT = 1
    ERR_CRC = 2

    def __init__(self, error_code, temperature, humidity):
        self.error_code = error_code
        self.temperature = temperature
        self.humidity = humidity

    def is_valid(self):
        return self.error_code == DHT22Result.ERR_NO_ERROR

class DHT22:
    def __init__(self, pin):
        self.pin = pin
        GPIO.setmode(GPIO.BCM)
    
    def read(self):
        # Send start signal
        GPIO.setup(self.pin, GPIO.OUT)
        GPIO.output(self.pin, GPIO.LOW)
        time.sleep(0.001)  # 1 ms low to start signal (minimum 1 ms for DHT22)
        GPIO.output(self.pin, GPIO.HIGH)
        time.sleep(0.00003)  # 30 us
        GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        # Collect data
        data = []
        count = 0
        max_count = 10000
        
        # Wait for sensor response: a LOW pulse (~80 us)
        while GPIO.input(self.pin) == GPIO.HIGH:
            count += 1
            if count > max_count:
                return DHT22Result(DHT22Result.ERR_TIMEOUT, 0, 0)
        
        # Wait for sensor response: a HIGH pulse (~80 us)
        count = 0
        while GPIO.input(self.pin) == GPIO.LOW:
            count += 1
            if count > max_count:
                return DHT22Result(DHT22Result.ERR_TIMEOUT, 0, 0)
        
        count = 0
        while GPIO.input(self.pin) == GPIO.HIGH:
            count += 1
            if count > max_count:
                return DHT22Result(DHT22Result.ERR_TIMEOUT, 0, 0)

        # Read 40 bits data
        for i in range(40):
            # wait for LOW
            count = 0
            while GPIO.input(self.pin) == GPIO.LOW:
                count += 1
                if count > max_count:
                    return DHT22Result(DHT22Result.ERR_TIMEOUT, 0, 0)

            # measure length of HIGH pulse
            count = 0
            while GPIO.input(self.pin) == GPIO.HIGH:
                count += 1
                if count > max_count:
                    return DHT22Result(DHT22Result.ERR_TIMEOUT, 0, 0)

            # 26-28us means 0, ~70us means 1 (count is proportional to time)
            if count > 50:  # threshold (adjust if needed)
                data.append(1)
            else:
                data.append(0)

        # Convert bits to bytes
        bytes_data = []
        for i in range(5):
            byte = 0
            for j in range(8):
                byte = (byte << 1) | data[i * 8 + j]
            bytes_data.append(byte)

        # Check checksum
        checksum = sum(bytes_data[0:4]) & 0xFF
        if bytes_data[4] != checksum:
            return DHT22Result(DHT22Result.ERR_CRC, 0, 0)

        # Calculate humidity and temperature
        humidity = ((bytes_data[0] << 8) + bytes_data[1]) * 0.1
        temp_raw = ((bytes_data[2] & 0x7F) << 8) + bytes_data[3]
        temperature = temp_raw * 0.1
        if (bytes_data[2] & 0x80):
            temperature = -temperature

        return DHT22Result(DHT22Result.ERR_NO_ERROR, temperature, humidity)


if __name__ == "__main__":
    sensor = DHT22(pin=4)  # GPIO4 (physical pin 7)
    try:
        result = sensor.read()
        if result.is_valid():
            print(f"Temperature: {result.temperature:.1f}°C")
            print(f"Humidity: {result.humidity:.1f}%")
        else:
            print(f"Error reading sensor, code: {result.error_code}")
    except KeyboardInterrupt:
        pass
    finally:
        GPIO.cleanup()
