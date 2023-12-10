from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db
from app.electric_price_checker import Webhooks


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

    def add_device(self, device_name, device_protocol, max_hours, active_hours_weekday, active_hours_weekend,
                   webhook=None):
        device = Device()
        device.device_name = device_name
        device.device_protocol = device_protocol
        device.webhook = webhook
        device.max_hours = max_hours
        self.devices.append(device)
        db.session.commit()

        for hour in active_hours_weekday:
            sleep_hours = SleepHours(hour=hour, is_active=True, is_weekend=False, device_id=device.device_id)
            db.session.add(sleep_hours)
        for hour in active_hours_weekend:
            sleep_hours = SleepHours(hour=hour, is_active=True, is_weekend=True, device_id=device.device_id)
            db.session.add(sleep_hours)

        db.session.commit()
        return device


class Device(db.Model):
    device_id = db.Column(db.Integer, primary_key=True)
    device_name = db.Column(db.String(120), index=True)
    device_protocol = db.Column(db.String(32), index=True)
    webhook = db.Column(db.String(128))
    max_hours = db.Column(db.Integer)
    status = db.Column(db.String(3), default='OFF')
    sleep_hours = db.relationship('SleepHours', back_populates='device', lazy='dynamic',
                                  primaryjoin="and_(Device.device_id==SleepHours.device_id, " 
                                              "SleepHours.is_weekend==False)", cascade="all, delete-orphan",
                                  overlaps="sleep_hours_weekend")
    sleep_hours_weekend = db.relationship('SleepHours', back_populates='device', lazy='dynamic',
                                          primaryjoin="and_(Device.device_id==SleepHours.device_id, "
                                                      "SleepHours.is_weekend==True)", cascade="all, delete-orphan",
                                          overlaps="sleep_hours")
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'))
    user = db.relationship('User', backref='devices')

    def turn_on(self):
        self.status = 'ON'
        if self.device_protocol == 'IFTTT':
            Webhooks().do_webhooks_request(self.webhook + '_down')
        elif self.device_protocol == 'GoogleAssistant':
            pass

    def turn_off(self):
        self.status = 'OFF'
        if self.device_protocol == 'IFTTT':
            Webhooks().do_webhooks_request(self.webhook + '_high')
        elif self.device_protocol == 'Google Assistant':
            pass

    def to_dict(self):
        return {
            'id': self.device_id,
            'name': self.device_name,
            'protocol': self.device_protocol,
            'webhook': self.webhook,
            'max_hours': self.max_hours,
            'status': self.status,
            'sleep_hours': [sleep_hour.to_dict() for sleep_hour in self.sleep_hours],
            'sleep_hours_weekend': [sleep_hour.to_dict() for sleep_hour in self.sleep_hours_weekend]
        }


class SleepHours(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hour = db.Column(db.Integer)
    is_active = db.Column(db.Boolean)
    is_weekend = db.Column(db.Boolean)
    device_id = db.Column(db.Integer, db.ForeignKey('device.device_id'), nullable=False)
    device = db.relationship('Device', back_populates='sleep_hours')

    def to_dict(self):
        return {
            'id': self.id,
            'hour': self.hour,
            'is_active': self.is_active,
            'is_weekend': self.is_weekend
        }


class BestHours(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, unique=True, nullable=False)


class Hour(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hour = db.Column(db.String(5), nullable=False)
    price = db.Column(db.Float, nullable=False)
    best_hour_id = db.Column(db.Integer, db.ForeignKey('best_hours.id'), nullable=False)
