import paho.mqtt.client as mqtt
import subprocess

MQTT_BROKER = "10.189.197.148"
MQTT_TOPIC = "locker/unlock"

def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker with result code " + str(rc))
    client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    payload = msg.payload.decode()
    print(f"Received MQTT message: {payload}")
    if payload == "unlock":
        print("Triggering Door.py...")
        subprocess.Popen(["python3", "/home/pi/Door.py"])

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(MQTT_BROKER, 1883, 60)
client.loop_forever()
