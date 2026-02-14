from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from config import DATABASE_URL
from models import db
from models.user import User
from models.scooter import Scooter
from models.ride import Ride
import os

# Определяем корневую папку проекта
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder=os.path.join(BASE_DIR, 'static'))
CORS(app, origins=["*"], allow_headers=["*"], supports_credentials=True)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return "<h1>Добро пожаловать в Whoosh API!</h1>"

@app.route('/tma')
def tma_index():
    try:
        return send_from_directory(
            os.path.join(BASE_DIR, 'static', 'tma'),
            'index.html'
        )
    except Exception as e:
        return f"Ошибка загрузки TMA: {str(e)}", 500

@app.route('/api/scooters')
def get_scooters():
    try:
        scooters = Scooter.query.all()
        result = [{
            'id': s.id,
            'imei': s.imei,
            'lat': s.lat,
            'lng': s.lng,
            'battery': s.battery,
            'status': s.status
        } for s in scooters]
        return jsonify(result)
    except Exception as e:
        return f"Ошибка API: {str(e)}", 500

@app.route('/generate_scooters_tuymazy')
def generate_scooters_tuymazy():
    from random import uniform, choice

    # Удаляем старые самокаты
    Scooter.query.delete()
    db.session.commit()

    center_lat = 54.6046
    center_lng = 53.7066

    statuses = ['available', 'available', 'available', 'in_use', 'offline']
    batteries = list(range(20, 101))  # от 20 до 100%

    scooters = []
    for i in range(1, 16):
        lat = round(center_lat + uniform(-0.01, 0.01), 6)
        lng = round(center_lng + uniform(-0.01, 0.01), 6)
        battery = choice(batteries)
        status = choice(statuses)

        s = Scooter(
            imei=f"35{str(i).zfill(13)}",
            lat=lat,
            lng=lng,
            battery=battery,
            status=status
        )
        scooters.append(s)
        db.session.add(s)

    db.session.commit()
    return f"✅ 15 самокатов добавлено в Туймазы!"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=False)