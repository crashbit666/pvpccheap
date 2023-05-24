from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, IntegerField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError
from app.models import User


class LoginForm(FlaskForm):
    username = StringField('User Name', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember me')
    submit = SubmitField('Submit')


class RegistrationForm(FlaskForm):
    username = StringField('User name', validators=[DataRequired()])
    user_mail = StringField('Email', validators=[DataRequired(), Email()])
    password1 = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField(
        'Repeat the password', validators=[DataRequired(), EqualTo('password1')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please, use another user name.')

    def validate_email(self, user_mail):
        user_mail = User.query.filter_by(user_mail=user_mail.data).first()
        if user_mail is not None:
            raise ValidationError('Please use another email.')


class DeviceForm(FlaskForm):
    device_name = StringField('Device Name', validators=[DataRequired()])
    max_hours = IntegerField('Max Hours', validators=[DataRequired()])
    sleep_hours = IntegerField('Sleep Hours', validators=[DataRequired()])
    sleep_hours_weekend = IntegerField('Sleep Hours Weekend', validators=[DataRequired()])
    submit = SubmitField('Add Device')
