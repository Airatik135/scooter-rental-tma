from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
from config import DATABASE_URL
from models import db
from models.user import User
from models.scooter import Scooter
from models.ride import Ride
import os
from random import uniform, choice

# Определяем корневую папку проекта
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder=os.path.join(BASE_DIR, 'static'))
CORS(app, origins=["*"], allow_headers=["*"], supports_credentials=True)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

import time

def init_db():
    for i in range(5):
        try:
            with app.app_context():
                db.create_all()
            print("✅ Таблицы созданы")
            return
        except Exception as e:
            print(f"[{i+1}/5] Ошибка инициализации: {e}")
            time.sleep(5)
    raise RuntimeError("Не удалось создать таблицы в PostgreSQL")

init_db()

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

@app.route('/tma/assets/images/<path:filename>')
def serve_image(filename):
    return send_from_directory(os.path.join(BASE_DIR, 'static', 'tma', 'assets', 'images'), filename)

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

@app.route('/add_test_scooters')
def add_test_scooters():
    try:
        Scooter.query.delete()
        db.session.commit()

        s1 = Scooter(imei="123456789012345", lat=55.75, lng=37.62, battery=90, status="available")
        s2 = Scooter(imei="123456789012346", lat=55.76, lng=37.63, battery=50, status="available")
        s3 = Scooter(imei="123456789012347", lat=55.77, lng=37.64, battery=20, status="offline")

        db.session.add(s1)
        db.session.add(s2)
        db.session.add(s3)
        db.session.commit()

        return "✅ 3 тестовых самоката добавлены!"
    except Exception as e:
        return f"Ошибка: {str(e)}", 500

@app.route('/api/tst100/webhook', methods=['POST'])
def tst100_webhook():
    try:
        data = request.get_json()
        print("Получен вебхук:", data)

        # Извлечение данных (адаптируем под реальный JSON из Flespi)
        imei = data.get('device', {}).get('imei') or data.get('imei')
        if not imei:
            return jsonify({"error": "IMEI not found"}), 400

        position = data.get('position', {})
        lat = position.get('latitude')
        lng = position.get('longitude')
        battery = data.get('battery.level') or data.get('battery')
        voltage = data.get('external.battery.voltage')
        speed = data.get('position.speed')
        odometer = data.get('vehicle.mileage')

        # Обновление в БД
        scooter = Scooter.query.filter_by(imei=imei).first()
        if scooter:
            scooter.lat = lat
            scooter.lng = lng
            scooter.battery = int(battery) if battery else scooter.battery
            scooter.speed = float(speed) if speed else 0.0
            scooter.odometer = int(odometer) if odometer else scooter.odometer
            scooter.last_seen = datetime.utcnow()
            db.session.commit()
            return jsonify({"status": "ok", "scooter_id": scooter.id}), 200
        else:
            return jsonify({"error": f"Scooter with IMEI {imei} not found"}), 404

    except Exception as e:
        print("Ошибка вебхука:", str(e))
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=False)