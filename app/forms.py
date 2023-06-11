from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, IntegerField, SelectMultipleField, widgets, \
    SelectField, Form, FormField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, NumberRange

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

    @staticmethod
    def validate_username(username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please, use another user name.')

    @staticmethod
    def validate_email(user_mail):
        user_mail = User.query.filter_by(user_mail=user_mail.data).first()
        if user_mail is not None:
            raise ValidationError('Please use another email.')


class IFTTTForm(Form):
    webhook = StringField('Webhook')


class DeviceForm(FlaskForm):
    device_name = StringField('Device name', validators=[DataRequired()])
    device_protocol = SelectField('Device Protocol', choices=[('Matter', 'Matter'), ('IFTTT', 'IFTTT')])
    ifttt_form = FormField(IFTTTForm)
    max_hours = IntegerField('Max hours', validators=[DataRequired(), NumberRange(min=0, max=24)])
    active_hours_weekday = SelectMultipleField('Weekday Active Hours', choices=[(hour, hour) for hour in range(24)],
                                               coerce=int, widget=widgets.ListWidget(prefix_label=False),
                                               option_widget=widgets.CheckboxInput())
    active_hours_weekend = SelectMultipleField('Weekend Active Hours', choices=[(hour, hour) for hour in range(24)],
                                               coerce=int, widget=widgets.ListWidget(prefix_label=False),
                                               option_widget=widgets.CheckboxInput())
    submit = SubmitField('Add Device')

    def validate_active_hours_weekday(self, field):
        if not field.data:
            raise ValidationError('Please select at least one hour.')

    def validate_active_hours_weekend(self, field):
        if not field.data:
            raise ValidationError('Please select at least one hour.')
