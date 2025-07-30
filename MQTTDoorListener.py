import paho.mqtt.client as mqtt
import subprocess

# Define MQTT Broker and Topics
MQTT_BROKER = "192.168.158.163"  # Replace with your MQTT broker IP
MQTT_TOPIC_UNLOCK = "locker/unlock"
MQTT_TOPIC_STATUS = "locker/status"

# Callback when the client connects to the broker
def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker with result code " + str(rc))
    # Subscribe to the topics you are interested in
    client.subscribe(MQTT_TOPIC_UNLOCK)
    client.subscribe(MQTT_TOPIC_STATUS)

# Callback when a message is received from the MQTT broker
def on_message(client, userdata, msg):
    payload = msg.payload.decode()
    print(f"Received MQTT message on topic {msg.topic}: {payload}")

    # If the message is to unlock the door, trigger the door control
    if msg.topic == MQTT_TOPIC_UNLOCK and payload == "unlock":
        print("Triggering Door.py...")
        subprocess.Popen(["python3", "/home/wenyuan/Desktop/Door.py"])

    # If the message is a door status update, log it
    elif msg.topic == MQTT_TOPIC_STATUS:
        print(f"Door status update: {payload}")
        # You can process or log this status if needed

# Create MQTT client instance
client = mqtt.Client()

# Assign callbacks
client.on_connect = on_connect
client.on_message = on_message

# Connect to the MQTT broker
client.connect(MQTT_BROKER, 1883, 60)

# Start the MQTT loop to continuously check for messages
client.loop_forever()
