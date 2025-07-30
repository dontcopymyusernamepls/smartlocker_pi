import tracemalloc
import asyncio
import websockets
import paho.mqtt.client as mqtt
import json
from weakref import WeakSet
import resource
import gc
import threading
import base64
from io import BytesIO
from PIL import Image
import face_recognition
import numpy as np

# Initialize memory tracking
tracemalloc.start()
resource.setrlimit(resource.RLIMIT_NOFILE, (8192, 8192))
gc.enable()

# Configuration
PING_TIMEOUT = 60
PING_INTERVAL = 30

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC_PIN = "locker/pin"
MQTT_TOPIC_SENSORS = "locker/sensors"
MQTT_TOPIC_UNLOCK = "locker/unlock"
MQTT_TOPIC_DOOR_STATUS = "locker/door_status"

current_pin = "111111"
connected_clients = WeakSet()

# Load known face encoding once at startup
known_image = face_recognition.load_image_file("known_face.jpg")
known_encodings = face_recognition.face_encodings(known_image)
if not known_encodings:
    raise RuntimeError("No face found in known_face.jpg")
known_encoding = known_encodings[0]

# MQTT callbacks
def on_mqtt_connect(client, userdata, flags, rc):
    print(f"MQTT connected with code {rc}")
    client.subscribe(MQTT_TOPIC_SENSORS)
    client.subscribe(MQTT_TOPIC_DOOR_STATUS)

def on_mqtt_disconnect(client, userdata, rc):
    print(f"MQTT disconnected with code {rc}")
    if rc != 0:
        client.reconnect()

def on_mqtt_message(client, userdata, msg):
    payload = msg.payload.decode()
    def send_to_ws(ws, payload):
        try:
            asyncio.run(ws.send(payload))
        except Exception as e:
            print(f"Failed to send WS: {e}")
            connected_clients.discard(ws)

    if msg.topic == MQTT_TOPIC_SENSORS:
        print(f"Forwarding sensor data: {payload}")
        for ws in list(connected_clients):
            threading.Thread(target=send_to_ws, args=(ws, payload)).start()
    elif msg.topic == MQTT_TOPIC_DOOR_STATUS:
        print(f"Door status update: {payload}")

mqtt_client = mqtt.Client(client_id='server')
mqtt_client.on_connect = on_mqtt_connect
mqtt_client.on_disconnect = on_mqtt_disconnect
mqtt_client.on_message = on_mqtt_message
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
mqtt_client.loop_start()

async def handle_websocket(websocket, path):
    print(f"New WS connection from {websocket.remote_address}")
    connected_clients.add(websocket)
    try:
        while True:
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=PING_INTERVAL)
                data = json.loads(message)

                # Handle PIN update
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

                # Handle door unlock command
                elif 'command' in data and data['command'] == 'unlock':
                    print("Unlock command received")
                    mqtt_client.publish(MQTT_TOPIC_UNLOCK, "unlock")
                    await websocket.send(json.dumps({
                        "status": "success",
                        "message": "Unlock command sent"
                    }))

                # Handle face authentication
                elif data.get('type') == 'face_auth':
                    base64_img = data.get('image', '')
                    if not base64_img:
                        await websocket.send(json.dumps({
                            "type": "face_auth_response",
                            "success": False,
                            "message": "No image data"
                        }))
                        continue

                    try:
                        img_bytes = base64.b64decode(base64_img)
                        img = Image.open(BytesIO(img_bytes)).convert('RGB')
                        img_np = np.array(img)

                        # Find face encodings in the received image
                        encodings = face_recognition.face_encodings(img_np)
                        if not encodings:
                            response = {
                                "type": "face_auth_response",
                                "success": False,
                                "message": "No face detected"
                            }
                        else:
                            # Compare against known encoding
                            results = face_recognition.compare_faces([known_encoding], encodings[0])
                            if results[0]:
                                mqtt_client.publish(MQTT_TOPIC_UNLOCK, "unlock")
                                response = {
                                    "type": "face_auth_response",
                                    "success": True,
                                    "message": "Face recognized. Locker unlocked!"
                                }
                            else:
                                response = {
                                    "type": "face_auth_response",
                                    "success": False,
                                    "message": "Face not recognized."
                                }
                        await websocket.send(json.dumps(response))

                    except Exception as e:
                        await websocket.send(json.dumps({
                            "type": "face_auth_response",
                            "success": False,
                            "message": f"Error processing image: {str(e)}"
                        }))

                else:
                    # Ignore unknown messages or extend handling here
                    pass

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
        print(f"WS connection closed: {websocket.remote_address}")
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
    asyncio.create_task(memory_monitor())

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

    snapshot = tracemalloc.take_snapshot()
    print("\nInitial memory snapshot:")
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
        snapshot = tracemalloc.take_snapshot()
        print("Final memory snapshot:")
        for stat in snapshot.statistics('lineno')[:3]:
            print(stat)
