import tracemalloc
import asyncio
import websockets
import paho.mqtt.client as mqtt
import json
from weakref import WeakSet
import resource
import gc
import threading
import firebase_admin
from firebase_admin import credentials, db

# Firebase setup
cred = credentials.Certificate("privateKey.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://smartpicklocker-default-rtdb.asia-southeast1.firebasedatabase.app/'
})

lockerStatus_ref = db.reference('Locker_status')
sensor_ref = db.reference('Sensors_data')



# Initialize memory tracking
tracemalloc.start()
resource.setrlimit(resource.RLIMIT_NOFILE, (8192, 8192))
gc.enable()

# Configuration
PING_TIMEOUT = 60  # 60 seconds
PING_INTERVAL = 30  # 30 seconds

# MQTT Configuration
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC_PIN = "locker/pin"
MQTT_TOPIC_SENSORS = "locker/sensors"
MQTT_TOPIC_UNLOCK = "locker/unlock"
MQTT_TOPIC_DOOR_STATUS = "locker/door_status"  # New topic for door status updates

# Store the current PIN
current_pin = "111111"

# WebSocket connections (using WeakSet for automatic cleanup)
connected_clients = WeakSet()

# ========== MQTT Setup ==========
def on_mqtt_connect(client, userdata, flags, rc):
    print(f"MQTT Broker connected with result code {rc}")
    client.subscribe(MQTT_TOPIC_SENSORS)
    client.subscribe(MQTT_TOPIC_DOOR_STATUS)  # Subscribe to door status updates

def on_mqtt_disconnect(client, userdata, rc):
    print(f"MQTT disconnected with code {rc}")
    if rc != 0:
        client.reconnect()

def on_mqtt_message(client, userdata, msg):
    payload = msg.payload.decode()
    
    # Thread-safe WebSocket send
    def send_to_ws(ws, payload):
        try:
            asyncio.run(ws.send(payload))
        except Exception as e:
            print(f"Failed to send to WebSocket: {e}")
            connected_clients.discard(ws)
    
    if msg.topic == MQTT_TOPIC_SENSORS:
        print(f"Forwarding sensor data: {payload}")  # Debug log
        # Forward to all connected WebSocket clients
        for ws in list(connected_clients):
            threading.Thread(target=send_to_ws, args=(ws, payload)).start()
    elif msg.topic == MQTT_TOPIC_DOOR_STATUS:
        print(f"Door status update: {payload}")

mqtt_client = mqtt.Client(client_id='server')
mqtt_client.on_connect = on_mqtt_connect
mqtt_client.on_message = on_mqtt_message
mqtt_client.on_disconnect = on_mqtt_disconnect
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
mqtt_client.loop_start()

# ========== WebSocket Server ==========
async def handle_websocket(websocket, path):
    print(f"New WebSocket connection from {websocket.remote_address}")
    connected_clients.add(websocket)
    try:
        while True:
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=PING_INTERVAL)
                data = json.loads(message)
                
                if 'pin' in data:
                    new_pin = data['pin'].strip()
                    if len(new_pin) == 6:
                        global current_pin
                        current_pin = new_pin
                        print(f"PIN updated: {current_pin}")
                        mqtt_client.publish(MQTT_TOPIC_PIN, json.dumps({"pin": current_pin}))
                        await websocket.send(json.dumps({"status": "success", "pin": current_pin}))
                    else:
                        await websocket.send(json.dumps({
                            "status": "error",
                            "message": "Invalid PIN length"
                        }))
                elif 'command' in data and data['command'] == 'unlock':
                    print("Sending unlock command to door")
                    mqtt_client.publish(MQTT_TOPIC_UNLOCK, "unlock")
                    await websocket.send(json.dumps({
                        "status": "success",
                        "message": "Unlock command sent"
                    }))
                    
            except asyncio.TimeoutError:
                await websocket.ping()
            except json.JSONDecodeError:
                await websocket.send(json.dumps({
                    "status": "error",
                    "message": "Invalid JSON format"
                }))
            except websockets.exceptions.ConnectionClosed:
                break
            except Exception as e:
                print(f"WebSocket error: {e}")
                break
    finally:
        connected_clients.discard(websocket)
        print(f"WebSocket connection closed: {websocket.remote_address}")
        try:
            await websocket.close()
        except:
            pass

async def memory_monitor():
    while True:
        await asyncio.sleep(60)
        snapshot = tracemalloc.take_snapshot()
        print("\nMemory stats (top 5):")
        for stat in snapshot.statistics('lineno')[:5]:
            print(stat)

async def main():
    # Start memory monitoring
    asyncio.create_task(memory_monitor())
    
    # Start WebSocket server
    server = await websockets.serve(
        handle_websocket,
        "0.0.0.0",
        8765,
        ping_interval=PING_INTERVAL,
        ping_timeout=PING_TIMEOUT,
        close_timeout=10,
        max_size=2**20  # 1MB max message size
    )
    
    print("Server started with:")
    print(f"- Ping interval: {PING_INTERVAL}s")
    print(f"- Ping timeout: {PING_TIMEOUT}s")
    print(f"- Max message size: 1MB")
    print(f"- Door control enabled via {MQTT_TOPIC_UNLOCK}")
    
    # Print initial memory stats
    print("\nInitial memory snapshot:")
    snapshot = tracemalloc.take_snapshot()
    for stat in snapshot.statistics('lineno')[:3]:
        print(stat)
    
    await server.wait_closed()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer shutting down...")
    finally:
        print("Cleaning up...")
        mqtt_client.disconnect()
        print("Final memory snapshot:")
        snapshot = tracemalloc.take_snapshot()
        for stat in snapshot.statistics('lineno')[:3]:
            print(stat)
