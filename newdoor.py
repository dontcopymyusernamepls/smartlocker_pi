from gpiozero import Servo
from gpiozero.pins.pigpio import PiGPIOFactory
from time import sleep
import paho.mqtt.client as mqtt
import json
import logging
from datetime import datetime

# === Setup Logging ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# === Servo Setup ===
try:
    factory = PiGPIOFactory()
    servo = Servo(17, pin_factory=factory, min_pulse_width=0.5/1000, max_pulse_width=2.5/1000)
    logger.info("Servo initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize servo: {e}")
    raise

# === MQTT Config ===
MQTT_BROKER = "192.168.158.163"  # IP of Pi A (MQTT broker)
MQTT_PORT = 1883
MQTT_TOPIC_UNLOCK = "locker/unlock"
MQTT_TOPIC_STATUS = "locker/door_status"
UNLOCK_DURATION = 30  # seconds door stays open

# === Servo Control Function ===
def unlock_locker():
    try:
        # Publish opening status
        publish_door_status("opening", "in_progress")
        
        logger.info("Unlocking the locker...")
        servo.max()  # Full unlock position
        sleep(1)  # Wait for door to fully open
        
        # Publish opened status
        publish_door_status("opened", "complete", {"remaining": UNLOCK_DURATION})
        
        logger.info(f"Door will stay unlocked for {UNLOCK_DURATION} seconds...")
        
        # Countdown timer
        for sec in range(UNLOCK_DURATION, 0, -1):
            if sec % 5 == 0 or sec <= 5:  # Update every 5 sec or last 5 sec
                publish_door_status("opened", "countdown", {"remaining": sec})
            sleep(1)
        
        # Publish closing status
        publish_door_status("closing", "in_progress")
        
        logger.info("Locking the locker...")
        servo.min()  # Full lock position
        sleep(2.5)  # Wait for door to fully close
        
        # Publish closed status
        publish_door_status("closed", "complete")
        
        logger.info("Returning servo to neutral position...")
        servo.mid()  # Return to center to reduce strain
        sleep(0.5)
        
    except Exception as e:
        logger.error(f"Error in unlock_locker: {e}")
        publish_door_status("error", "failed", {"message": str(e)})

def publish_door_status(action, status, extra_data=None):
    """Helper function to publish standardized status messages"""
    message = {
        "action": action,
        "status": status,
        "timestamp": datetime.now().isoformat()
    }
    if extra_data:
        message.update(extra_data)
    
    client.publish(
        topic=MQTT_TOPIC_STATUS,
        payload=json.dumps(message),
        qos=1,
        retain=False
    )
    logger.debug(f"Published status: {message}")

# === MQTT Callbacks ===
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("Connected to MQTT Broker")
        client.subscribe(MQTT_TOPIC_UNLOCK, qos=1)
        publish_door_status("system", "online")
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
            publish_door_status("warning", "invalid_command", {"received": payload})
            
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        publish_door_status("error", "message_processing_failed", {"error": str(e)})

# === MQTT Setup ===
client = mqtt.Client(client_id="door_controller")
client.on_connect = on_connect
client.on_message = on_message

# Configure Last Will and Testament
client.will_set(
    MQTT_TOPIC_STATUS,
    payload=json.dumps({
        "action": "system",
        "status": "offline",
        "timestamp": datetime.now().isoformat()
    }),
    qos=1,
    retain=True
)

# === Main Execution ===
if __name__ == '__main__':
    try:
        logger.info(f"Connecting to MQTT broker at {MQTT_BROKER}...")
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        
        logger.info("Starting Door MQTT listener...")
        client.loop_forever()
        
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
        publish_door_status("system", "shutdown")
        client.disconnect()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        publish_door_status("error", "fatal_error", {"error": str(e)})
        raise
