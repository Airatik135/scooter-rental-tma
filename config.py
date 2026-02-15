import os

# Токен бота из @BotFather
TELEGRAM_BOT_TOKEN = '8366931411:AAER-fkSsCj-tNn7ovB3oWOzsY0YVtAKXzY'

# Ключи от ЮKassa
YOOKASSA_SHOP_ID = 'your_shop_id'
YOOKASSA_SECRET_KEY = 'your_secret_key'

# Настройки БД
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///scooters.db')

# Порт Flask-сервера
FLASK_PORT = 5000