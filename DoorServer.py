from flask import Flask, request, jsonify

app = Flask(__name__)

door_alert = None

@app.route('/door-alert', methods=['POST'])
def receive_alert():
    global door_alert
    data = request.get_json()
    print("Received door alert:", data)
    door_alert = data
    return jsonify({"status": "received"}), 200

@app.route('/door-status', methods=['GET'])
def get_door_status():
    return jsonify({"door_alert": door_alert}), 200
