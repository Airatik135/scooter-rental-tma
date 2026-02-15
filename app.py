from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
from config import DATABASE_URL
from models import db
from models.user import User
from models.scooter import Scooter
from models.ride import Ride
import os
import requests
from datetime import datetime
import time
from sqlalchemy import text

# Определяем корневую папку проекта
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder=os.path.join(BASE_DIR, 'static'))
CORS(app, origins=["*"], allow_headers=["*"], supports_credentials=True)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ——— FLESPI TOKEN ———
FLESPI_TOKEN = os.getenv('FLESPI_TOKEN', 'YOUR_FLESPI_TOKEN_HERE')

def send_command_to_tst100(device_id, command):
    """
    Отправляет команду на TST100 через Flespi
    command: 'sclockctrl 0' (разблокировать) или 'sclockctrl 1' (заблокировать)
    device_id: ID устройства в Flespi (например, 7738860)
    """
    if FLESPI_TOKEN == 'YOUR_FLESPI_TOKEN_HERE':
        print("⚠️ FLESPI_TOKEN не установлен в переменных окружения")
        return False

    # ✅ Правильный URL: через Device ID
    url = f"https://flespi.io/gw/devices/{device_id}/commands/send"
    
    payload = {
        "commands": [command]  # Команда
    }
    
    headers = {
        "Authorization": f"FlespiToken {FLESPI_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"Команда '{command}' отправлена. Ответ: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Команда успешно отправлена в Flespi")
        else:
            print(f"❌ Ошибка: {response.text}")
        
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Ошибка отправки команды: {e}")
        return False

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

                # ——— ДОБАВИТЬ РЕАЛЬНЫЙ САМОКАТ ———
                existing = Scooter.query.filter_by(imei="350544507678012").first()
                if not existing:
                    real_scooter = Scooter(
                        imei="350544507678012",
                        lat=54.828638,
                        lng=55.866863,
                        battery=91,
                        speed=6.0,
                        odometer=3024291,
                        status="available"
                    )
                    db.session.add(real_scooter)
                    db.session.commit()
                    print("✅ Реальный самокат добавлен")

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
        print("ПОЛУЧЕННЫЙ JSON:", data)

        # Извлечение IMEI (в TST100 это поле 'ident')
        imei = data.get('ident')
        if not imei:
            print("❌ IMEI не найден в JSON (поле 'ident')")
            return jsonify({"error": "IMEI not found"}), 400

        # Извлечение координат
        position = data.get('position', {})
        lat = position.get('latitude')
        lng = position.get('longitude')
        speed = position.get('speed')
        altitude = position.get('altitude')

        # Извлечение других данных
        battery_level = data.get('scooter.battery.level') or data.get('battery.level')
        voltage = data.get('external.powersource.voltage') or data.get('internal.battery.voltage')
        odometer = data.get('vehicle.mileage')  # в км
        lock_status = data.get('lock.status')
        ignition_status = data.get('engine.ignition.status')
        remaining_mileage = data.get('predicted.remaining.mileage')

        # Поиск самоката в БД
        scooter = Scooter.query.filter_by(imei=imei).first()
        if scooter:
            # Обновляем данные
            if lat is not None:
                scooter.lat = lat
            if lng is not None:
                scooter.lng = lng
            if battery_level is not None:
                scooter.battery = int(battery_level)
            if speed is not None:
                scooter.speed = float(speed)
            if odometer is not None:
                scooter.odometer = int(odometer * 1000)  # км → метры (если в БД хранится в метрах)
            scooter.last_seen = datetime.utcnow()

            # Обновляем статус (можно добавить логику)
            if lock_status is not None:
                scooter.status = 'locked' if lock_status else 'available'
            elif ignition_status is not None and not ignition_status:
                scooter.status = 'offline'

            db.session.commit()
            print(f"✅ Самокат {scooter.id} обновлён:")
            print(f"   - Координаты: {lat}, {lng}")
            print(f"   - Заряд: {battery_level}%")
            print(f"   - Скорость: {speed} km/h")
            print(f"   - Пробег: {odometer} km")
            return jsonify({"status": "ok", "scooter_id": scooter.id}), 200
        else:
            print(f"❌ Самокат с IMEI {imei} не найден в БД")
            return jsonify({"error": f"Scooter with IMEI {imei} not found"}), 404

    except Exception as e:
        print("❌ Ошибка вебхука:", str(e))
        return jsonify({"error": str(e)}), 500

@app.route('/api/rent/<int:scooter_id>', methods=['POST'])
def rent_scooter(scooter_id):
    try:
        scooter = Scooter.query.get_or_404(scooter_id)

        if scooter.status != 'available':
            return jsonify({"success": False, "message": "Самокат недоступен для аренды"}), 400

        # Изменяем статус
        scooter.status = 'in_use'
        db.session.commit()

        # Отправляем команду разблокировки в TST100
        # ✅ Используем Device ID из Flespi (найди его в панели)
        success = send_command_to_tst100(device_id=7738860, command="sclockctrl 0")
        if success:
            message = "Самокат успешно арендован и разблокирован"
        else:
            message = "Самокат арендован, но не удалось отправить команду разблокировки"

        return jsonify({
            "success": True,
            "message": message,
            "scooter": {
                "id": scooter.id,
                "status": scooter.status
            }
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/end_rent/<int:scooter_id>', methods=['POST'])
def end_rent_scooter(scooter_id):
    try:
        scooter = Scooter.query.get_or_404(scooter_id)

        if scooter.status != 'in_use':
            return jsonify({"success": False, "message": "Самокат не находится в аренде"}), 400

        # Изменяем статус
        scooter.status = 'available'
        db.session.commit()

        # Отправляем команду блокировки в TST100
        success = send_command_to_tst100(device_id=7738860, command="sclockctrl 1")
        if success:
            message = "Аренда успешно завершена и самокат заблокирован"
        else:
            message = "Аренда завершена, но не удалось отправить команду блокировки"

        return jsonify({
            "success": True,
            "message": message,
            "scooter": {
                "id": scooter.id,
                "status": scooter.status
            }
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/scooters')
def get_scooters():
    try:
        # Возвращаем только реальный самокат
        scooter = Scooter.query.filter_by(imei="350544507678012").first()
        if scooter:
            result = [{
                'id': scooter.id,
                'imei': scooter.imei,
                'lat': scooter.lat,
                'lng': scooter.lng,
                'battery': scooter.battery,
                'status': scooter.status,
                'speed': scooter.speed,
                'odometer': scooter.odometer
            }]
        else:
            result = []
        return jsonify(result)
    except Exception as e:
        return f"Ошибка API: {str(e)}", 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=False)