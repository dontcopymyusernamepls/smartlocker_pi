import socket
import json
import threading
import os
import time

HOST = '0.0.0.0'
PORT = 9000

shared_data = {'pin': '111111'}
SENSOR_DATA_FILE = '/home/smartlocker/stats/sensor_data.json'
IR_STATE_FILE = '/home/smartlocker/stats/ir_sensor.json'

def handle_client(conn, addr):
    print(f"[TCP] Connected by {addr}")
    try:
        while True:
            data = conn.recv(1024).decode()
            if not data:
                break
            try:
                request = json.loads(data)
                command = request.get('command')

                if command == 'set-pin':
                    new_pin = request.get('pin')
                    if new_pin and len(new_pin) == 6:
                        shared_data['pin'] = new_pin
                        response = {'status': 'success', 'pin': new_pin}
                    else:
                        response = {'status': 'error', 'message': 'Invalid pin'}

                elif command == 'get-pin':
                    response = {'pin': shared_data['pin']}

                elif command == 'locker-statistics':
                    response = {
                        "status": "success",
                        "temperature": None,
                        "humidity": None,
                        "timestamp": time.time(),
                        "locker_empty": None,
                        "message": ""
                    }

                    # Load sensor data
                    if os.path.exists(SENSOR_DATA_FILE):
                        with open(SENSOR_DATA_FILE) as f:
                            sensor_data = json.load(f)
                            response.update({
                                "temperature": sensor_data.get("temperature"),
                                "humidity": sensor_data.get("humidity"),
                                "timestamp": sensor_data.get("timestamp")
                            })

                    # Load IR data
                    if os.path.exists(IR_STATE_FILE):
                        with open(IR_STATE_FILE) as f:
                            ir_data = json.load(f)
                            response["locker_empty"] = ir_data.get("locker_empty")
                            response["message"] = ir_data.get("message")

                else:
                    response = {'status': 'error', 'message': 'Unknown command'}

            except Exception as e:
                response = {'status': 'error', 'message': str(e)}

            conn.sendall(json.dumps(response).encode())

    finally:
        conn.close()
        print(f"[TCP] Connection with {addr} closed.")

def start_tcp_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[TCP] Server listening on {HOST}:{PORT}")
    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr)).start()

if __name__ == '__main__':
    start_tcp_server()
