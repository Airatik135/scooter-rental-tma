import os

# Принудительно используем SQLite
DATABASE_URL = 'sqlite:///scooters.db'

# Чтобы PostgreSQL не использовался, даже если в переменных окружения
# DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///scooters.db')