from gpiozero import Servo
from gpiozero.pins.pigpio import PiGPIOFactory
from time import sleep
import paho.mqtt.client as mqtt
import json
import logging

# === Setup Logging ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# === Servo Setup ===
try:
    factory = PiGPIOFactory()
    servo = Servo(17, pin_factory=factory)
    logger.info("Servo initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize servo: {e}")
    raise

# === MQTT Config ===
MQTT_BROKER = "192.168.158.163"  # Replace with IP of Pi A (MQTT broker)
MQTT_PORT = 1883
MQTT_TOPIC_UNLOCK = "locker/unlock"
MQTT_TOPIC_STATUS = "locker/door_status"

# === Servo Control Function ===
def unlock_locker():
    try:
        logger.info("Unlocking the locker...")
        servo.max()
        sleep(1)
        
        client.publish(MQTT_TOPIC_STATUS, "unlocked", qos=1)
        
        logger.info("Door will stay unlocked for 30 seconds...")
        sleep(30)
        
        logger.info("Locking the locker...")
        servo.min()
        sleep(2.5)
        
        client.publish(MQTT_TOPIC_STATUS, "locked", qos=1)
        
        logger.info("Returning servo to center (rest)...")
        servo.mid()
        sleep(1)
        
    except Exception as e:
        logger.error(f"Error in unlock_locker: {e}")
        client.publish(MQTT_TOPIC_STATUS, f"error: {str(e)}", qos=1)

# === MQTT Callbacks ===
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("Connected to MQTT Broker")
        client.subscribe(MQTT_TOPIC_UNLOCK, qos=1)
    else:
        logger.error(f"Connection failed with code {rc}")

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode().strip().lower()
        logger.info(f"Received message on {msg.topic}: {payload}")
        
        if payload == "unlock":
            unlock_locker()
        else:
            logger.warning(f"Ignoring unknown command: {payload}")
            
    except Exception as e:
        logger.error(f"Error processing message: {e}")

# === MQTT Setup ===
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.will_set(MQTT_TOPIC_STATUS, payload="offline", qos=1, retain=True)

try:
    logger.info(f"Connecting to MQTT broker at {MQTT_BROKER}...")
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    
    client.publish(MQTT_TOPIC_STATUS, "online", qos=1, retain=True)
    
    logger.info("Starting Door MQTT listener...")
    client.loop_forever()

except KeyboardInterrupt:
    logger.info("Shutting down gracefully...")
    client.publish(MQTT_TOPIC_STATUS, "offline", qos=1, retain=True)
    client.disconnect()

except Exception as e:
    logger.error(f"Fatal error: {e}")
    client.publish(MQTT_TOPIC_STATUS, f"error: {str(e)}", qos=1, retain=True)
    raise
