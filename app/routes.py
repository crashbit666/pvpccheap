from flask import render_template, flash, redirect, url_for, request, current_app
from flask_login import current_user, login_user, logout_user, login_required
from urllib.parse import urlsplit
from app import app, db
from app.forms import LoginForm, RegistrationForm, DeviceForm
from app.models import User


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
        current_user.add_device(form.device_name.data, form.max_hours.data,
                                form.sleep_hours.data, form.sleep_hours_weekend.data)
        flash('Your device has been added.')
        return redirect(url_for('index'))
    return render_template('add_device.html', form=form)


@current_app.route('/')
@current_app.route('/index')
@login_required
def index():
    # devices = current_user.devices.all()
    devices = current_user.devices
    return render_template('index.html', devices=devices)
