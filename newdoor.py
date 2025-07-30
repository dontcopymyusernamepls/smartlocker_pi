from gpiozero import Servo
from gpiozero.pins.pigpio import PiGPIOFactory
from time import sleep
import paho.mqtt.client as mqtt
import json

# === Servo Setup ===
factory = PiGPIOFactory()
servo = Servo(17, pin_factory=factory)

# === MQTT Config ===
MQTT_BROKER = "192.168.158.163"  # IP of Pi A (MQTT broker)
MQTT_PORT = 1883
MQTT_TOPIC_UNLOCK = "locker/unlock"

# === Servo Control Function ===
def unlock_locker():
    print("Unlocking the locker...")
    servo.max()
    sleep(1)

    print("Door will stay unlocked for 30 seconds...")
    sleep(30)

    print("Locking the locker...")
    servo.min()
    sleep(2.5)

    print("Returning servo to center (rest)...")
    servo.mid()
    sleep(1)

# === MQTT Callbacks ===
def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT Broker with result code", rc)
    client.subscribe(MQTT_TOPIC_UNLOCK)

def on_message(client, userdata, msg):
    print(f"Received message on {msg.topic}: {msg.payload.decode()}")
    try:
        payload = json.loads(msg.payload.decode())
        if payload.get("action") == "unlock":
            unlock_locker()
    except Exception as e:
        print("Error parsing message:", e)

# === MQTT Setup ===
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_forever()
