from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db


class User(UserMixin, db.Model):
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    user_mail = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return self.user_id

    def add_device(self, device_name, max_hours, sleep_hours, sleep_hours_weekend):
        new_device = Device(device_name=device_name, max_hours=max_hours,
                            sleep_hours=sleep_hours, sleep_hours_weekend=sleep_hours_weekend, user=self)
        db.session.add(new_device)
        db.session.commit()
"""
class Device(db.Model):
    device_id = db.Column(db.Integer, primary_key=True)
    device_name = db.Column(db.String(120), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'))
    user = db.relationship('User', backref='devices')
"""


class Device(db.Model):
    device_id = db.Column(db.Integer, primary_key=True)
    device_name = db.Column(db.String(120), index=True)
    max_hours = db.Column(db.Integer)
    sleep_hours = db.Column(db.Integer)
    sleep_hours_weekend = db.Column(db.Integer)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'))
    user = db.relationship('User', backref='devices')
