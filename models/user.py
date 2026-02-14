from . import db  # импорт db из __init__.py

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    telegram_id = db.Column(db.BigInteger, unique=True, nullable=False)
    phone = db.Column(db.String(20))
    card_token = db.Column(db.String(255))
    balance = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=db.func.now())