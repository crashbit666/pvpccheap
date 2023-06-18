from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_jwt_extended import JWTManager
from flask_apscheduler import APScheduler
from app.electric_price_checker import ElectricPriceChecker, ElectricPriceCheckerException
from app.date_time_helper import DateTimeHelper
from app.bbdd_secrets import dbsecrets
from app.api_secrets import apisecrets as secrets
from app.api_secrets import jwt_secrets as jwt_secrets
from flask_cors import CORS

db = SQLAlchemy()
login_manager = LoginManager()
scheduler = APScheduler()
jwt = JWTManager()


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


@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data):
    from app.models import User
    identity = jwt_data["sub"]
    return User.query.get(identity)


def create_app():
    app = Flask(__name__)
    CORS(app, resources={r"/*": {"origins": "*"}})

    app.config['SECRET_KEY'] = dbsecrets.get('DATABASE_SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = dbsecrets.get('SQLALCHEMY_DATABASE_URI')

    app.config["JWT_SECRET_KEY"] = jwt_secrets.get('JWT_SECRET_KEY')

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    jwt.init_app(app)
    scheduler.init_app(app)
    scheduler.start()

    @scheduler.task('cron', id='check_devices', minute='0')
    def check_devices():
        with app.app_context():
            from app.models import Device, SleepHours, Hour, BestHours
            timezone = 'Europe/Madrid'
            date, hour, weekday = DateTimeHelper(timezone).get_date()
            hour_str = str(hour).zfill(2)

            # Delete old records
            old_hours_records = Hour.query.join(BestHours).filter(BestHours.date < date).all()
            for record in old_hours_records:
                db.session.delete(record)

            old_best_hours_records = BestHours.query.filter(BestHours.date < date).all()
            for record in old_best_hours_records:
                db.session.delete(record)

            db.session.commit()

            # Search if today's best hours are already in DB
            best_hours_record = BestHours.query.filter_by(date=date).first()

            if best_hours_record is None:
                # If prices are not found, update them
                update_prices()
                best_hours_record = BestHours.query.filter_by(date=date).first()

            if best_hours_record is not None:
                cheap_hours = [hour.hour for hour in Hour.query.filter_by(best_hour_id=best_hours_record.id).all()]
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
            else:
                print("Doesn't exist a record for today's best hours.")

    def update_prices():
        with app.app_context():
            from app.models import BestHours, Hour
            timezone = 'Europe/Madrid'
            date, _, _ = DateTimeHelper(timezone).get_date()

            # DELETE this block on PRODUCTION !!!!!!!
            """
            existing_record = BestHours.query.filter_by(date=date).first()
            if existing_record is not None:
                # Deleting all the Hour records related to this BestHours record
                Hour.query.filter_by(best_hour_id=existing_record.id).delete()
                # Deleting the BestHours record
                db.session.delete(existing_record)
                db.session.commit()
                print(f"Best prices for date {date} already existed and were deleted.")
            # DELETE this block on PRODUCTION !!!!!!! IMPORTANT !!!!!!!
            """

            # Create a new BestHours record
            new_best_hours_record = BestHours(date=date)
            db.session.add(new_best_hours_record)
            db.session.commit()

            try:
                cheap_hours = ElectricPriceChecker(secrets, timezone).get_best_hours(date)

                # Store today's best hours in the database
                for hour_price in cheap_hours:
                    hour, price = hour_price
                    db.session.add(Hour(hour=hour, price=price, best_hour_id=new_best_hours_record.id))

                db.session.commit()
            except ElectricPriceCheckerException as e:
                print(f"Error connecting to ESIOS API. Exception: {e}")

    with app.app_context():
        from . import routes, models
        db.create_all()
        check_devices()

    return app
