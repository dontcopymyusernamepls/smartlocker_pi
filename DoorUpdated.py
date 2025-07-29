from gpiozero import Servo
from gpiozero.pins.pigpio import PiGPIOFactory
from time import sleep, time
import requests

# Setup servo on GPIO17 using pigpio
factory = PiGPIOFactory()
servo = Servo(17, pin_factory=factory)

WAIT_TIME = 10
MAX_DOOR_CLOSE_TIME = 30
DOOR_CLOSED = True  # Replace this with a sensor check if available

DOOR_SERVER = 'http://10.189.197.148:5000'  # Replace with your actual DoorServer IP if different

try:
    print("🔓 Starting Smart Door Sequence...")

    # === Step 1: Clear any old alerts when door is unlocked ===
    try:
        response = requests.post(f"{DOOR_SERVER}/clear-alert",
                                 json={"status": "Parcel collected", "timestamp": time()})
        print("✅ Alert cleared from dashboard:", response.status_code)
    except Exception as e:
        print("❌ Failed to clear alert:", e)

    # === Step 2: Unlock the locker ===
    print("🔓 Unlocking the locker")
    servo.max()
    sleep(1)

    print("⏱️ Door will stay unlocked for 30 seconds...")
    sleep(30)

    # === Step 3: Lock the locker ===
    print("🔒 Locking the locker")
    servo.min()
    sleep(2.5)

    print("🔄 Returning servo to center (rest)...")
    servo.mid()
    sleep(1)

    # === Step 4: Monitor door state (simulate for now) ===
    print("🕵️ Monitoring if door remains closed for too long...")
    start_time = time()

    while DOOR_CLOSED:
        elapsed = time() - start_time
        if elapsed > MAX_DOOR_CLOSE_TIME:
            print("🚨 ALERT: Door has remained closed too long!")

            # Send 3-day alert
            try:
                response = requests.post(
                    f"{DOOR_SERVER}/door-alert",
                    json={"alert": "Parcel has not been collected for more than 3 days.",
                          "timestamp": time()}
                )
                print("📡 Alert sent to dashboard:", response.status_code)
            except Exception as e:
                print("❌ Failed to send alert:", e)
            break
        sleep(1)

except Exception as e:
    print(f"💥 Error occurred: {e}")

finally:
    servo.mid()
    sleep(1)
    print("✅ Script finished cleanly.")
