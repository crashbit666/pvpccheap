# This is a program that search the best hours to charge electric devices.
# Version: Beta 5
import datetime
import json
import time
import pytz
import logging
import logging.handlers
import firebase_admin
from firebase_admin import credentials, db
from webhooks import do_webhooks_request
import requests as requests
from secrets import secrets


class ElectricPriceChecker:
    def __init__(self, secrets, timezone):
        self.token = secrets.get('TOKEN')
        self.url = secrets.get('URL')
        self.timezone = timezone

    def cheap_price(self, in_cheap_hours, in_current_time):
        # Here we need to check if past hour is expensive or cheap hour. If the hour is not cheap, the last status
        # will be False

        if in_current_time in in_cheap_hours:
            return True
        else:
            return False

    def get_best_hours(self, max_items, actual_date):
        local_timezone = pytz.timezone(self.timezone)
        start_date = local_timezone.localize(datetime.datetime.combine(actual_date, datetime.time(0, 0, 0)),
                                             is_dst=None).isoformat()
        end_date = local_timezone.localize(datetime.datetime.combine(actual_date, datetime.time(23, 0, 0)),
                                           is_dst=None).isoformat()

        headers = {'Accept': 'application/json; application/vnd.esios-api-v2+json', 'Content-Type': 'application/json',
                   'Host': 'api.esios.ree.es', 'x-api-key': self.token}

        pkw = []
        hours = []

        response = requests.get(self.url + '?start_date=' + start_date + '&end_date='
                                + end_date + '&geo_ids[]=8741', headers=headers)

        if response.status_code == 200:
            json_data = json.loads(response.text)
            vals = json_data['indicator']['values']
            prices = [x['value'] for x in vals]
            for price in prices:
                pkw.append(round(price / 1000, 4))
        else:
            pkw = "Error connecting to database"

        # Next four lines format ESIOS data. Enumerate data for hours, sort and remove price.
        pkw = sorted(list(enumerate(pkw)), key=lambda k: k[1])[0:max_items]
        for i in pkw:
            hours.append(i[0])

        logger.info("Best hours: %s", hours)
        return hours


class Logger:
    def __init__(self):
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.DEBUG)  # Set to logging.INFO to reduce verbosity
        handler = logging.handlers.SysLogHandler(address='/dev/log')
        formatter = logging.Formatter('%(module)s.%(funcName)s: %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def info(self, message):
        self.logger.info(message)

    def debug(self, message):
        self.logger.debug(message)

    def error(self, message):
        self.logger.error(message)


class FirebaseHandler:
    def __init__(self, credential_path, database_url):
        cred = credentials.Certificate(credential_path)
        firebase_admin.initialize_app(cred, {'databaseURL': database_url})
        self.db = db.reference()

    def get_max_hours(self):
        ref = self.db.child('max_hours')
        return ref.get()

    def get_sleep_hours(self, device_name):
        ref = self.db.child(f'devices/{device_name}/sleep_hours')
        return ref.get()

    def get_sleep_hours_weekend(self, device_name):
        ref = self.db.child(f'devices/{device_name}/sleep_hours_weekend')
        return ref.get()


class DateTimeHelper:
    def __init__(self, timezone):
        self.timezone = timezone

    def get_dates(self):
        local_timezone = pytz.timezone(self.timezone)
        local_dt = datetime.datetime.now(local_timezone)
        logger.info("Hour: %s", local_dt.hour)
        return local_dt.date(), local_dt.hour, local_dt.weekday()

    def delay_to_oclock(self):
        minutes = int(datetime.datetime.now().strftime("%M"))
        return 60 - minutes


class Device:
    def __init__(self, name, webhook_key, sleep_hours, sleep_hours_weekend):
        self.name = name
        self.webhook_key = webhook_key
        self.sleep_hours = sleep_hours
        self.sleep_hours_weekend = sleep_hours_weekend
        self.actual_status = False

    def activate(self):
        self.actual_status = True

    def deactivate(self):
        self.actual_status = False

    def process_device(device, device_status, webhook_key):
        if device_status:
            if not device.actual_status:
                device.activate()
                while not do_webhooks_request(webhook_key + '_pvpc_down'):
                    time.sleep(1)
        else:
            if device.actual_status:
                device.deactivate()
                while not do_webhooks_request(webhook_key + '_pvpc_high'):
                    time.sleep(1)


# Start point
if __name__ == '__main__':

    # Initialize logger
    logger = Logger()

    # Initialize Firebase
    firebase_handler = FirebaseHandler(
        secrets.get('JSON_FILE'), secrets.get('FIREBASE_URL')
    )

    # Initialize DateTimeHelper and ElectricPriceChecker
    electric_price_checker = ElectricPriceChecker(secrets, 'Europe/Madrid')
    datetime_helper = DateTimeHelper('Europe/Madrid')

    # Initialize devices
    devices = [
        Device("Scooter", "scooter", None, None),
        Device("Boiler", "boiler", None, None),
        Device("Papas Stove", "papas_stove", firebase_handler.get_sleep_hours('papas_stove'),
               firebase_handler.get_sleep_hours_weekend('papas_stove')),
        Device("Enzo Stove", "enzo_stove", firebase_handler.get_sleep_hours('enzo_stove'),
               firebase_handler.get_sleep_hours_weekend('enzo_stove'))
    ]

    # Initialize current_day, current_time and cheap_hours
    max_hours = firebase_handler.get_max_hours()
    current_day, current_time, current_week_day = datetime_helper.get_dates()
    cheap_hours = electric_price_checker.get_best_hours(max_hours, current_day)

    # Infinite loop
    while True:
        delay = 60 * datetime_helper.delay_to_oclock()  # get delay time until o'clock

        current_time = datetime_helper.get_dates()[1]  # get current hour

        # Check if current_day == actual date, if not, update current_day to actual date and cheap_hours.
        if current_day != datetime_helper.get_dates()[0]:
            current_day = datetime_helper.get_dates()[0]
            current_week_day = datetime_helper.get_dates()[2]
            cheap_hours = electric_price_checker.get_best_hours(max_hours, current_day)

        is_cheap = electric_price_checker.cheap_price(cheap_hours, current_time)
        is_weekend = current_week_day >= 5

        for device in devices:
            if device.sleep_hours is None:  # Devices without sleep hours, such as Scooter and Boiler
                device.process_device(device, is_cheap, device.webhook_key)
            else:  # Devices with sleep hours, such as Papas Stove and Enzo Stove
                device_status = is_cheap and (
                        current_time in (device.sleep_hours_weekend if is_weekend else device.sleep_hours))
                device.process_device(device, device_status, device.webhook_key)

        time.sleep(delay)
# Final line
