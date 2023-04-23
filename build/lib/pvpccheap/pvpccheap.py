# This is a program that search the best hours to charge electric devices.
# Version: Beta 6
import datetime
import json
import time
import pytz
import logging
import logging.handlers
import firebase_admin
from firebase_admin import credentials, db
import requests as requests
from pvpccheap.secrets import secrets


class Webhooks:
    def __init__(self, webhook_apikey):
        self.webhook_apikey = webhook_apikey

    def do_webhooks_request(self, pvpc):
        try:
            requests.post(f'https://maker.ifttt.com/trigger/{pvpc}/with/key/{self.webhook_apikey}')
            return True
        except requests.ConnectionError:
            return False
        except requests.HTTPError:
            return False
        except requests.TooManyRedirects:
            return False
        except requests.Timeout:
            time.sleep(3)
            return False


class ElectricPriceChecker:
    def __init__(self, _secrets, timezone, logger):
        self.token = _secrets.get('TOKEN')
        self.url = _secrets.get('URL')
        self.timezone = timezone
        self.logger = logger

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

        response = requests.get(f"{self.url}?start_date={start_date}&end_date={end_date}&geo_ids[]=8741",
                                headers=headers)

        if response.status_code == 200:
            json_data = json.loads(response.text)
            vals = json_data['indicator']['values']
            prices = [x['value'] for x in vals]
            for price in prices:
                pkw.append(round(price / 1000, 4))
        else:
            self.logger.debug("Error connecting to ESIOS API. Status code: %s" % response.status_code)
            raise ElectricPriceCheckerException("Error connecting to ESIOS API.")

        # Next four lines format ESIOS data. Enumerate data for hours, sort and remove price.
        pkw = sorted(list(enumerate(pkw)), key=lambda k: k[1])[0:max_items]
        for i in pkw:
            hours.append(i[0])

        self.logger.debug("Best hours: %s" % hours)
        return hours


class ElectricPriceCheckerException(Exception):
    pass


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
    def __init__(self, credential_path, database_url, logger):
        cred = credentials.Certificate(credential_path)
        firebase_admin.initialize_app(cred, {'databaseURL': database_url})
        self.db = db.reference()
        self.logger = logger

    def get_max_hours(self):
        ref = self.db.child('max_hours')
        self.logger.debug("Max hours: %s" % ref.get())
        return ref.get()

    def get_sleep_hours(self, device_name):
        ref = self.db.child(f'devices/{device_name}/sleep_hours')
        self.logger.debug("Sleep hours: %s" % ref.get())
        return ref.get()

    def get_sleep_hours_weekend(self, device_name):
        ref = self.db.child(f'devices/{device_name}/sleep_hours_weekend')
        self.logger.debug("Sleep hours weekend: %s" % ref.get())
        return ref.get()


class DateTimeHelper:
    def __init__(self, timezone, logger):
        self.timezone = timezone
        self.logger = logger

    def get_dates(self):
        local_timezone = pytz.timezone(self.timezone)
        local_dt = datetime.datetime.now(local_timezone)
        self.logger.info("Hour: %s, Date: %s, Weekday: %s" % (local_dt.hour, local_dt.date(), local_dt.weekday()))
        return local_dt.date(), local_dt.hour, local_dt.weekday()


class Device:
    def __init__(self, name, webhook_key, sleep_hours, sleep_hours_weekend, logger, webhooks):
        self.name = name
        self.webhook_key = webhook_key
        self.sleep_hours = sleep_hours
        self.sleep_hours_weekend = sleep_hours_weekend
        self.actual_status = False
        self.logger = logger
        self.webhooks = webhooks

    def activate(self):
        self.actual_status = True

    def deactivate(self):
        self.actual_status = False

    def process_device(self, _device_status):
        if _device_status:
            if not self.actual_status:
                self.activate()
                while not self.webhooks.do_webhooks_request('_pvpc_down'):
                    time.sleep(1)
        else:
            if self.actual_status:
                self.deactivate()
                while not self.webhooks.do_webhooks_request('_pvpc_high'):
                    time.sleep(1)

        self.logger.debug("Device status for %s: %s" % (self.name, "ON" if _device_status else "OFF"))
        self.logger.debug("Current status for %s: %s" % (self.name, "ON" if self.actual_status else "OFF"))


def update_cheap_hours(_electric_price_checker, _max_hours, _current_day, logger):
    try:
        return _electric_price_checker.get_best_hours(_max_hours, _current_day)
    except ElectricPriceCheckerException as ex:
        logger.error("Error getting cheap hours: %s" % str(ex))
        return []


def is_in_cheap_hours(in_cheap_hours, in_current_time):
    return in_current_time in in_cheap_hours


def main():
    # Initialize logger
    logger = Logger()

    # Initialize Firebase
    firebase_handler = FirebaseHandler(
        secrets.get('JSON_FILE'), secrets.get('FIREBASE_URL'), logger
    )

    # Initialize DateTimeHelper and ElectricPriceChecker
    electric_price_checker = ElectricPriceChecker(secrets, 'Europe/Madrid', logger)
    datetime_helper = DateTimeHelper('Europe/Madrid', logger)

    # Initialize webhooks
    webhooks = Webhooks(secrets.get('WEBHOOKS_KEY'))

    # Initialize devices
    devices = [
        Device("Scooter", "scooter", None, None, logger, webhooks),
        Device("Boiler", "boiler", None, None, logger, webhooks),
        Device("Papas Stove", "papas_stove", firebase_handler.get_sleep_hours('papas_stove'),
               firebase_handler.get_sleep_hours_weekend('papas_stove'), logger, webhooks),
        Device("Enzo Stove", "enzo_stove", firebase_handler.get_sleep_hours('enzo_stove'),
               firebase_handler.get_sleep_hours_weekend('enzo_stove'), logger, webhooks)
    ]

    # Initialize current_day, current_time and cheap_hours
    max_hours = firebase_handler.get_max_hours()
    current_day, current_time, current_week_day = datetime_helper.get_dates()
    cheap_hours = update_cheap_hours(electric_price_checker, max_hours, current_day, logger)

    # Infinite loop
    while True:
        # get delay time until o'clock
        delay = (60 - datetime.datetime.now().minute) * 60

        # get current date, hour, and weekday
        current_date, current_time, current_week_day = datetime_helper.get_dates()

        # Check if current_day == actual date, if not, update current_day to actual date and cheap_hours.
        if current_day != current_date:
            current_day = current_date
            current_week_day = current_week_day
            try:
                cheap_hours = update_cheap_hours(electric_price_checker, max_hours, current_day, logger)
            except ElectricPriceCheckerException as e:
                logger.error("Error getting cheap hours: %s" % str(e))
                continue

        is_cheap = is_in_cheap_hours(cheap_hours, current_time)
        is_weekend = current_week_day >= 5

        for device in devices:
            if device.sleep_hours is None:  # Devices without sleep hours, such as Scooter and Boiler
                device.process_device(is_cheap)
            else:  # Devices with sleep hours, such as Papas Stove and Enzo Stove
                device_status = is_cheap and (
                        current_time in (device.sleep_hours_weekend if is_weekend else device.sleep_hours))
                device.process_device(device_status)

        time.sleep(delay)


# Start point
if __name__ == '__main__':
    main()
# Final line