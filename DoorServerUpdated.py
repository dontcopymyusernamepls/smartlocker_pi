from flask import Flask, request, jsonify

app = Flask(__name__)

door_alert = None  # Holds the latest alert message

# ========== POST: Send Alert ==========
@app.route('/door-alert', methods=['POST'])
def receive_alert():
    global door_alert
    data = request.get_json()
    print("🚨 Received door alert:", data)
    door_alert = data
    return jsonify({"status": "received"}), 200

# ========== GET: Fetch Current Alert ==========
@app.route('/door-status', methods=['GET'])
def get_door_status():
    return jsonify({"door_alert": door_alert}), 200

# ========== POST: Clear Alert ==========
@app.route('/clear-alert', methods=['POST'])
def clear_alert():
    global door_alert
    print("✅ Clearing alert")
    door_alert = None
    return jsonify({"message": "Alert cleared"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
