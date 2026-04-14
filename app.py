from flask import Flask, request, jsonify, send_from_directory
from core import IRCTCSystem, Passenger, PassengerType, Gender
import os

app = Flask(__name__, static_folder='static', static_url_path='')

system = IRCTCSystem([3, 4, 6])

@app.route('/')
def serve_index():
    return send_from_directory('static', 'index.html')

@app.route('/api/state', methods=['GET'])
def get_state():
    return jsonify(system.get_state())

@app.route('/api/book', methods=['POST'])
def book_ticket():
    data = request.json
    passengers_data = data.get('passengers', [])
    batch = []
    for pd in passengers_data:
        p_type = PassengerType.TATKAL if data.get('ticket_type') == 'tatkal' else PassengerType.NORMAL
        gen = Gender.MALE if pd.get('gender') == 'M' else Gender.FEMALE
        batch.append(Passenger(
            name=pd.get('name'),
            p_type=p_type,
            gender=gen,
            prefers_rac=pd.get('prefers_rac', False)
        ))
    
    if data.get('ticket_type') == 'tatkal' and not system.tatkal_window_open:
        return jsonify({"success": False, "error": "Tatkal window is closed."}), 400
        
    logs = system.process_bulk_booking(batch)
    return jsonify({"success": True, "logs": logs, "state": system.get_state()})

@app.route('/api/cancel', methods=['POST'])
def cancel_ticket():
    data = request.json
    name = data.get('name')
    if not name:
        return jsonify({"success": False, "error": "Name required"}), 400
    logs = system.cancel_by_name(name)
    return jsonify({"success": True, "logs": logs, "state": system.get_state()})

@app.route('/api/tatkal/toggle', methods=['POST'])
def toggle_tatkal():
    system.tatkal_window_open = not system.tatkal_window_open
    return jsonify({"success": True, "tatkal_open": system.tatkal_window_open})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
