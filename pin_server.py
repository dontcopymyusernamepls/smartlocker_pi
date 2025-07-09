from flask import Flask, request

app = Flask(__name__)
shared_data = {'pin': '111111'}  # Default

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
