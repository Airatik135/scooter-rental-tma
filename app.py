import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS 
from config import DATABASE_URL

from models import db
from models.user import User
from models.scooter import Scooter
from models.ride import Ride

app = Flask(__name__)
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return "<h1>Добро пожаловать в Whoosh API!</h1>"

app.static_folder = 'static'

@app.route('/tma')
def tma_index():
    return app.send_static_file('tma/index.html')

@app.route('/api/scooters')
def get_scooters():
    scooters = Scooter.query.all()
    result = []
    for s in scooters:
        result.append({
            'id': s.id,
            'imei': s.imei,
            'lat': s.lat,
            'lng': s.lng,
            'battery': s.battery,
            'status': s.status
        })
    return jsonify(result)

@app.route('/add_test_scooters')
def add_test_scooters():
    from models.scooter import Scooter

    # Удалим старые данные (для теста)
    Scooter.query.delete()

    # Добавим 3 тестовых самоката
    s1 = Scooter(imei="123456789012345", lat=55.75, lng=37.62, battery=90, status="available")
    s2 = Scooter(imei="123456789012346", lat=55.76, lng=37.63, battery=50, status="available")
    s3 = Scooter(imei="123456789012347", lat=55.77, lng=37.64, battery=20, status="offline")

    db.session.add(s1)
    db.session.add(s2)
    db.session.add(s3)
    db.session.commit()

    return "3 тестовых самоката добавлены!"    

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 8080))  # ← важно: 8080, а не 5000
    app.run(host='0.0.0.0', port=port, debug=False)
