import paho.mqtt.client as mqtt
#import firebase_admin
# firebase_admin import credentials, db
import asyncio
import websockets
import paho.mqtt.client as mqtt
import json

id = 'server'
#port = 1883
#broker = 'localhost'
#mqtt_client = mqtt.Client(client_id=id, callback_api_version=mqtt.CallbackAPIVersion.VERSION2)

        
# MQTT Configuration
MQTT_BROKER = "localhost"  # PI A's own IP(192.168.158.163)
MQTT_PORT = 1883
MQTT_TOPIC_PIN = "locker/pin"
MQTT_TOPIC_SENSORS = "locker/sensors"
MQTT_TOPIC_UNLOCK = "locker/unlock"

# Store the current PIN
current_pin = "111111"

# WebSocket connections
connected_clients = set()

# ========== MQTT Setup ==========
def on_mqtt_connect(client, userdata, flags, rc):
    print(f"MQTT Broker connected with result code {rc}")
    client.subscribe(MQTT_TOPIC_SENSORS)

def on_mqtt_message(client, userdata, msg):
    # Forward sensor data to all WebSocket clients
    if msg.topic == MQTT_TOPIC_SENSORS:
        for ws in connected_clients:
            asyncio.create_task(ws.send(msg.payload.decode()))

mqtt_client = mqtt.Client(client_id=id, callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
mqtt_client.on_connect = on_mqtt_connect
mqtt_client.on_message = on_mqtt_message
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
mqtt_client.loop_start()

# ========== WebSocket Server ==========
async def handle_websocket(websocket, path):
    connected_clients.add(websocket)
    try:
        async for message in websocket:
            data = json.loads(message)
            if 'pin' in data:  # New PIN from app
                new_pin = data['pin'].strip()  # Add strip() to remove whitespace
                if len(new_pin) == 6:
                    global current_pin
                    current_pin = new_pin
                    print(f"Received new PIN from app: {current_pin}")  # Debug log
                    # Broadcast to PI B via MQTT
                    mqtt_client.publish(MQTT_TOPIC_PIN, json.dumps({"pin": current_pin}))
                    await websocket.send(json.dumps({"status": "success", "pin": current_pin}))
                else:
                    await websocket.send(json.dumps({"status": "error", "message": "Invalid PIN length"}))
    finally:
        connected_clients.remove(websocket)

start_server = websockets.serve(handle_websocket, "0.0.0.0", 8765)


def run_mqtt():
	mqtt_client.connect(broker, port)
	mqtt_client.subscribe("maintopic/subtopic")
	mqtt_client.loop_forever()
	
def on_message(client, userdata, msg):
	payload = msg.payload.decode()
	print(f"Received: {msg.topic} = {payload}")
	
	if(msg.topic == 'maintopic/subtopic'):
		client.publish("dashboard/display", payload)
		client.publish("log/archive", f"Temp:{payload}")
	
# ========== Main ==========
if __name__ == '__main__':
	#mqtt_client.on_message = on_messager
	print("Starting WebSocket server and MQTT broker...")
	asyncio.get_event_loop().run_until_complete(start_server)
	asyncio.get_event_loop().run_forever()
	
	#mqtt_thread = threading.Thread(target=run_mqtt)
	#mqtt_thread.start()
		

