from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_apscheduler import APScheduler
from app.electric_price_checker import ElectricPriceChecker, ElectricPriceCheckerException
from app.date_time_helper import DateTimeHelper
from app.bbdd_secrets import dbsecrets
from app.api_secrets import apisecrets as secrets

db = SQLAlchemy()
login_manager = LoginManager()
scheduler = APScheduler()


@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return User.query.get(int(user_id))


@login_manager.request_loader
def load_user_from_request(request):
    from app.models import User
    user_id = request.headers.get('X-Auth-User')
    if user_id:
        return User.query.get(int(user_id))
    return None


@scheduler.task('cron', id='check_devices', minute='0')
def check_devices():
    from app.models import Device, SleepHours, Hour, BestHours
    timezone = 'Europe/Madrid'
    date, hour, weekday = DateTimeHelper(timezone).get_date()
    hour_str = str(hour).zfill(2)
    best_hours_record = BestHours.query.filter_by(date=date).first()

    if best_hours_record is None:
        # If prices are not found, update them
        update_prices('today')
        best_hours_record = BestHours.query.filter_by(date=date).first()

    cheap_hours = [hour.hour for hour in Hour.query.filter_by(best_hour_id=best_hours_record.id, type='today').all()]
    devices = Device.query.all()

    for device in devices:
        if weekday < 5:
            active_hours = [sleep_hour.hour for sleep_hour in device.sleep_hours]
        else:
            active_hours = [sleep_hour.hour for sleep_hour in device.sleep_hours_weekend]

        if hour_str in cheap_hours[:device.max_hours] and hour in active_hours:
            device.turn_on()
        else:
            device.turn_off()

        db.session.commit()


@scheduler.task('cron', id='update_prices', hour=23, minute=45)
def update_prices(day='tomorrow'):
    from app.models import BestHours, Hour
    timezone = 'Europe/Madrid'
    date, _, _ = DateTimeHelper(timezone).get_date()

    # Create BestHours record if it doesn't exist
    best_hours_record = BestHours.query.filter_by(date=date).first()
    if best_hours_record is None:
        best_hours_record = BestHours(date=date)
        db.session.add(best_hours_record)
        db.session.commit()

    if day == 'today':
        try:
            cheap_hours_today = ElectricPriceChecker(secrets, timezone).get_best_hours(date, days_ahead=0)

            # Store today's best hours in the database
            for hour in cheap_hours_today:
                db.session.add(Hour(hour=hour, best_hour_id=best_hours_record.id, type='today'))

            db.session.commit()
        except ElectricPriceCheckerException as e:
            print(f"Error connecting to ESIOS API. Exception: {e}")
    elif day == 'tomorrow':
        try:
            cheap_hours_tomorrow = ElectricPriceChecker(secrets, timezone).get_best_hours(date, days_ahead=1)

            # Store tomorrow's best hours in the database
            for hour in cheap_hours_tomorrow:
                db.session.add(Hour(hour=hour, best_hour_id=best_hours_record.id, type='tomorrow'))

            db.session.commit()
        except ElectricPriceCheckerException as e:
            print(f"Error connecting to ESIOS API. Exception: {e}")


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = dbsecrets.get('DATABASE_SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = dbsecrets.get('SQLALCHEMY_DATABASE_URI')

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    scheduler.init_app(app)
    scheduler.start()

    with app.app_context():
        from . import routes, models
        db.create_all()
        check_devices()

    return app
