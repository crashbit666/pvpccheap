from flask import render_template, flash, redirect, url_for, request, current_app, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from flask_login import current_user, login_user, logout_user, login_required
from urllib.parse import urlsplit
from app import db
from app.forms import LoginForm, RegistrationForm, DeviceForm
from app.models import User, Device


@current_app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or urlsplit(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Login', form=form)


@current_app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@current_app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, user_mail=form.user_mail.data)
        user.set_password(form.password1.data)
        db.session.add(user)
        db.session.commit()
        flash('Register is done')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@current_app.route('/add_device', methods=['GET', 'POST'])
@login_required
def add_device():
    form = DeviceForm()
    if form.validate_on_submit():
        if form.device_protocol.data == 'IFTTT' and not form.ifttt_form.webhook.data:
            flash('Webhook is required for IFTTT protocol.')
            return render_template('add_device.html', form=form)
        weekday_hours = [int(hour) for hour in form.active_hours_weekday.data]
        weekend_hours = [int(hour) for hour in form.active_hours_weekend.data]
        webhook = form.ifttt_form.webhook.data if form.device_protocol.data == 'IFTTT' else None
        current_user.add_device(
            form.device_name.data,
            form.device_protocol.data,
            form.max_hours.data,
            weekday_hours,
            weekend_hours,
            webhook
        )
        flash('Your device has been added.')
        return redirect(url_for('index'))
    form.active_hours_weekday.choices = [(str(hour), str(hour)) for hour in range(24)]
    form.active_hours_weekend.choices = [(str(hour), str(hour)) for hour in range(24)]
    return render_template('add_device.html', form=form)


@current_app.route('/remove_device/<int:device_id>', methods=['POST'])
@login_required
def remove_device(device_id):
    device = Device.query.get(device_id)
    if device is None or device.user != current_user:
        flash('Device not found.')
        return redirect(url_for('index'))
    db.session.delete(device)
    db.session.commit()
    flash('Your device has been removed.')
    return redirect(url_for('index'))


@current_app.route('/')
@current_app.route('/index')
@login_required
def index():
    devices = current_user.devices
    return render_template('index.html', devices=devices)


@current_app.route('/electricity_price')
def electricity_price():
    # Get today's date
    import datetime
    from app.models import BestHours, Hour

    today = datetime.date.today()

    # Get the record for today's best hours
    best_hours_record = BestHours.query.filter_by(date=today).first()

    # If there's no record for today, then there are no prices to display
    if best_hours_record is None:
        electric_prices = []
    else:
        # Get the prices for each of today's best hours
        electric_prices = Hour.query.filter_by(best_hour_id=best_hours_record.id).all()

    # Pass the prices to the template
    return render_template('electricity_price.html', electric_prices=electric_prices)


# ---------------- API ----------------
@current_app.route('/api/devices', methods=['GET'])
@jwt_required()
def get_devices():
    # Obtain the identity of the current user from the JWT
    current_user_id = get_jwt_identity()
    # Search the user in the database
    _current_user = User.query.get(current_user_id)

    if _current_user is not None:
        # Create a list with the devices of the user
        devices = [device.to_dict() for device in _current_user.devices]
        # Return devices in JSON format
        return jsonify(devices), 200
    else:
        #  doesn't have any authenticated user, return 401
        return {'message': 'User not authenticated'}, 401


@current_app.route('/api/login', methods=['POST'])
def api_login():
    if not request.is_json:
        return jsonify({"msg": "Missing JSON in request"}), 400

    username = request.json.get('username', None)
    password = request.json.get('password', None)

    if not username:
        return jsonify({"msg": "Missing username parameter"}), 400
    if not password:
        return jsonify({"msg": "Missing password parameter"}), 400

    user = User.query.filter_by(username=username).first()
    if user is None or not user.check_password(password):
        return jsonify({"msg": "Bad username or password"}), 401

    # If authentication is successful, create a JWT token
    access_token = create_access_token(identity=user.user_id)

    return jsonify(access_token=access_token), 200


@current_app.route('/api/electricity_price', methods=['GET'])
def get_electricity_price():
    import datetime
    from app.models import BestHours, Hour

    today = datetime.date.today()
    best_hours_record = BestHours.query.filter_by(date=today).first()

    if best_hours_record is None:
        electric_prices = []
    else:
        electric_prices = Hour.query.filter_by(best_hour_id=best_hours_record.id).all()

    # Transform results into JSON format
    electric_prices = [{'hour': x.hour, 'price': x.price} for x in electric_prices]

    return jsonify(electric_prices)


@current_app.route('/api/sleep_hours/<int:device_id>', methods=['GET'])
@jwt_required()
def get_sleep_hours(device_id):
    # Obtain the identity of the current user from the JWT
    current_user_id = get_jwt_identity()
    # Search the user in the database
    _current_user = User.query.get(current_user_id)

    if _current_user is not None:
        # Find the device with the given device_id
        device = Device.query.filter_by(device_id=device_id, user=_current_user).first()

        if device is not None:
            # Get the sleep hours for the device
            sleep_hours = device.sleep_hours.all()
            sleep_hours_weekend = device.sleep_hours_weekend.all()

            # Create dictionaries for the sleep hours
            sleep_hours_data = [{'hour': hour.hour, 'is_active': hour.is_active} for hour in sleep_hours]
            sleep_hours_weekend_data = [{'hour': hour.hour, 'is_active': hour.is_active} for hour in sleep_hours_weekend]

            # Return the sleep hours in JSON format
            return jsonify({'sleep_hours': sleep_hours_data, 'sleep_hours_weekend': sleep_hours_weekend_data}), 200
        else:
            # Device not found
            return jsonify({'message': 'Device not found'}), 404
    else:
        # User not authenticated
        return jsonify({'message': 'User not authenticated'}), 401
