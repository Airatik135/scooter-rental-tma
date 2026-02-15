from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
from config import DATABASE_URL
from models import db
from models.user import User
from models.scooter import Scooter
from models.ride import Ride
import os
from random import uniform, choice
from datetime import datetime
import time
from sqlalchemy import text

# Определяем корневую папку проекта
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder=os.path.join(BASE_DIR, 'static'))
CORS(app, origins=["*"], allow_headers=["*"], supports_credentials=True)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def init_db():
    for i in range(5):
        try:
            with app.app_context():
                db.create_all()

                # ——— ДОБАВИТЬ КОЛОНКИ ВРУЧНУЮ ———
                conn = db.engine.connect()

                # Проверим, есть ли колонка speed
                try:
                    conn.execute(text("SELECT speed FROM scooter LIMIT 1;"))
                except Exception:
                    print("Добавляем колонку speed...")
                    conn.execute(text("ALTER TABLE scooter ADD COLUMN speed NUMERIC DEFAULT 0.0;"))

                # Проверим, есть ли odometer
                try:
                    conn.execute(text("SELECT odometer FROM scooter LIMIT 1;"))
                except Exception:
                    print("Добавляем колонку odometer...")
                    conn.execute(text("ALTER TABLE scooter ADD COLUMN odometer INTEGER DEFAULT 0;"))

                # last_seen
                try:
                    conn.execute(text("SELECT last_seen FROM scooter LIMIT 1;"))
                except Exception:
                    print("Добавляем колонку last_seen...")
                    conn.execute(text("ALTER TABLE scooter ADD COLUMN last_seen DATETIME;"))

                conn.commit()
                print("✅ Таблицы обновлены")

            return
        except Exception as e:
            print(f"[{i+1}/5] Ошибка инициализации: {e}")
            time.sleep(5)
    raise RuntimeError("Не удалось создать таблицы в SQLite")

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

@app.route('/api/tst100/webhook', methods=['POST'])
def tst100_webhook():
    try:
        data = request.get_json()
        print("Вебхук получен:", data)

        # Извлечение IMEI
        imei = data.get('device', {}).get('imei') or data.get('imei')
        if not imei:
            return jsonify({"error": "IMEI not found"}), 400

        # Извлечение данных
        position = data.get('position', {})
        lat = position.get('latitude')
        lng = position.get('longitude')
        battery = data.get('battery.level') or data.get('battery')
        voltage = data.get('external.battery.voltage')
        speed = data.get('position.speed')
        odometer = data.get('vehicle.mileage')

        # Обновление самоката в БД
        scooter = Scooter.query.filter_by(imei=imei).first()
        if scooter:
            scooter.lat = lat
            scooter.lng = lng
            if battery is not None:
                scooter.battery = int(battery)
            if speed is not None:
                scooter.speed = float(speed)
            if odometer is not None:
                scooter.odometer = int(odometer)
            scooter.last_seen = datetime.utcnow()
            db.session.commit()
            print(f"✅ Самокат {scooter.id} обновлён по вебхуку")
            return jsonify({"status": "ok", "scooter_id": scooter.id}), 200
        else:
            print(f"⚠️ Самокат с IMEI {imei} не найден")
            return jsonify({"error": f"Scooter with IMEI {imei} not found"}), 404

    except Exception as e:
        print("Ошибка вебхука:", str(e))
        return jsonify({"error": str(e)}), 500

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
            'status': s.status,
            'speed': s.speed,
            'odometer': s.odometer
        } for s in scooters]
        return jsonify(result)
    except Exception as e:
        return f"Ошибка API: {str(e)}", 500

@app.route('/generate_scooters_tuymazy')
def generate_scooters_tuymazy():
    try:
        Scooter.query.delete()
        db.session.commit()

        center_lat = 54.6046
        center_lng = 53.7066

        statuses = ['available', 'available', 'available', 'in_use', 'offline']
        batteries = list(range(20, 101))

        for i in range(1, 16):
            lat = round(center_lat + uniform(-0.01, 0.01), 6)
            lng = round(center_lng + uniform(-0.01, 0.01), 6)
            battery = choice(batteries)
            status = choice(statuses)

            s = Scooter(
                imei=f"35{i:013}",
                lat=lat,
                lng=lng,
                battery=battery,
                status=status,
                speed=0.0,
                odometer=0
            )
            db.session.add(s)

        db.session.commit()
        return f"✅ 15 самокатов добавлено в Туймазы!"
    except Exception as e:
        return f"Ошибка: {str(e)}", 500

@app.route('/add_real_scooter')
def add_real_scooter():
    try:
        # Проверим, есть ли уже такой самокат
        existing = Scooter.query.filter_by(imei="350544507678012").first()
        if existing:
            db.session.delete(existing)
            db.session.commit()

        # Создаём самокат
        real_scooter = Scooter(
            imei="350544507678012",
            lat=54.8288017,  # начальные координаты
            lng=55.8661017,
            battery=93,
            status="available",
            speed=0.0,
            odometer=3024291
        )
        db.session.add(real_scooter)
        db.session.commit()
        return "✅ Реальный самокат добавлен!"
    except Exception as e:
        return f"❌ Ошибка: {str(e)}"        

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=False)