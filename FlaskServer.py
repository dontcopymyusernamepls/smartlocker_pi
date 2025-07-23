from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)
shared_data = {'pin': '111111'}
IR_STATUS_FILE = '/home/pi/shared/ir_status.json'

@app.route('/set-pin', methods=['POST'])
def set_pin():
    data = request.get_json()
    new_pin = data.get('pin')
    if new_pin and len(new_pin) == 6:
        shared_data['pin'] = new_pin
        return {'status': 'success', 'pin': new_pin}
    return {'status': 'error', 'message': 'Invalid pin'}, 400

@app.route('/get-pin', methods=['GET'])
def get_pin():
    return {'pin': shared_data['pin']}

@app.route('/locker-statistics', methods=['GET'])
def locker_statistics():
    try:
        if not os.path.exists(IR_STATUS_FILE):
            return jsonify({"status": "error", "message": "IR status not available"}), 500

        with open(IR_STATUS_FILE, 'r') as f:
            data = json.load(f)

        locker_empty = data.get("locker_empty", "unknown")

        return jsonify({
            "Locker Empty?": "Yes" if locker_empty == "yes" else "No"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
