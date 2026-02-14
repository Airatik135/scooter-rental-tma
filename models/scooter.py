from . import db

class Scooter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    imei = db.Column(db.String(15), unique=True, nullable=False)
    lat = db.Column(db.Float)
    lng = db.Column(db.Float)
    battery = db.Column(db.Integer)
    speed_limit = db.Column(db.Integer)
    status = db.Column(db.String(20), default='available')
    current_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    last_seen = db.Column(db.DateTime)