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

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)  # Set to logging.INFO to reduce verbosity
handler = logging.handlers.SysLogHandler(address='/dev/log')
formatter = logging.Formatter('%(module)s.%(funcName)s: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Configure logging system
logger.info("Firebase initialized")


def get_best_hours(max_items, actual_date):
    local_timezone = pytz.timezone('Europe/Madrid')
    start_date = local_timezone.localize(datetime.datetime.combine(actual_date, datetime.time(0, 0, 0)),
                                         is_dst=None).isoformat()
    end_date = local_timezone.localize(datetime.datetime.combine(actual_date, datetime.time(23, 0, 0)),
                                       is_dst=None).isoformat()

    token = secrets.get('TOKEN')
    url = secrets.get('URL')
    headers = {'Accept': 'application/json; application/vnd.esios-api-v2+json', 'Content-Type': 'application/json',
               'Host': 'api.esios.ree.es', 'x-api-key': token}

    pkw = []
    hours = []

    response = requests.get(url + '?start_date=' + start_date + '&end_date='
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

    # log best hours
    logger.info("Best hours: %s", hours)
    return hours


def get_dates():
    local_timezone = pytz.timezone('Europe/Madrid')
    local_dt = datetime.datetime.now(local_timezone)
    logger.info("Hour: %s", local_dt.hour)
    return local_dt.date(), local_dt.hour, local_dt.weekday()


def cheap_price(in_cheap_hours, in_current_time):
    # Here we need to check if past hour is expensive or cheap hour. If the hour is not cheap, the last status
    # will be False

    if in_current_time in in_cheap_hours:
        return True
    else:
        return False


def delay_to_oclock():
    minutes = int(datetime.datetime.now().strftime("%M"))
    return 60 - minutes


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


class ISwitch:

    def __init__(self, actual_status):
        self.actual_status = actual_status

    def activate(self):
        self.actual_status = True

    def deactivate(self):
        self.actual_status = False


# Start point
if __name__ == '__main__':

    # Initialize Firebase
    firebase_handler = FirebaseHandler(
        secrets.get('JSON_FILE'), secrets.get('FIREBASE_URL')
    )

    # Instance class
    Scooter_Switch = ISwitch(False)
    Boiler_Switch = ISwitch(False)
    Papas_Stove = ISwitch(False)
    Enzo_Stove = ISwitch(False)

    while not do_webhooks_request('scooter_pvpc_high'):
        time.sleep(1)
    while not do_webhooks_request('boiler_pvpc_high'):
        time.sleep(1)
    while not do_webhooks_request('papas_stove_pvpc_high'):
        time.sleep(1)
    while not do_webhooks_request('enzo_stove_pvpc_high'):
        time.sleep(1)

    # Initialize current_day, current_time and cheap_hours
    max_hours = firebase_handler.get_max_hours()

    current_day, current_time, current_week_day = get_dates()
    cheap_hours = get_best_hours(max_hours, current_day)

    papas_sleep_hours = firebase_handler.get_sleep_hours('papas_stove')
    papas_sleep_hours_weekend = firebase_handler.get_sleep_hours_weekend('papas_stove')
    enzo_sleep_hours = firebase_handler.get_sleep_hours('enzo_stove')
    enzo_sleep_hours_weekend = firebase_handler.get_sleep_hours_weekend('enzo_stove')

    # Infinite loop
    while True:
        delay = 60 * delay_to_oclock()  # get delay time until o'clock

        current_time = get_dates()[1]

        # Check if current_day == actual date, if not, update current_day to actual date and cheap_hours.
        if current_day != get_dates()[0]:
            current_day = get_dates()[0]
            current_week_day = get_dates()[2]
            cheap_hours = get_best_hours(max_hours, current_day)

        if cheap_price(cheap_hours, current_time):
            if not Scooter_Switch.actual_status:
                Scooter_Switch.activate()
                while not do_webhooks_request('scooter_pvpc_down'):
                    time.sleep(1)
            if not Boiler_Switch.actual_status:
                Boiler_Switch.activate()
                while not do_webhooks_request('boiler_pvpc_down'):
                    time.sleep(1)
            if not Papas_Stove.actual_status:
                if current_week_day < 5:
                    if current_time in papas_sleep_hours:
                        Papas_Stove.activate()
                        while not do_webhooks_request('papas_stove_pvpc_down'):
                            time.sleep(1)
                else:
                    if current_time in papas_sleep_hours_weekend:
                        Papas_Stove.activate()
                        while not do_webhooks_request('papas_stove_pvpc_down'):
                            time.sleep(1)
            if not Enzo_Stove.actual_status:
                if current_week_day < 5:
                    if current_time in enzo_sleep_hours:
                        Enzo_Stove.activate()
                        while not do_webhooks_request('enzo_stove_pvpc_down'):
                            time.sleep(1)
                else:
                    if current_time in enzo_sleep_hours_weekend:
                        Enzo_Stove.activate()
                        while not do_webhooks_request('enzo_stove_pvpc_down'):
                            time.sleep(1)

        else:
            if Scooter_Switch.actual_status:
                Scooter_Switch.deactivate()
                while not do_webhooks_request('scooter_pvpc_high'):
                    time.sleep(1)
            if Boiler_Switch.actual_status:
                Boiler_Switch.deactivate()
                while not do_webhooks_request('boiler_pvpc_high'):
                    time.sleep(1)
            if Papas_Stove.actual_status:
                Papas_Stove.deactivate()
                while not do_webhooks_request('papas_stove_pvpc_high'):
                    time.sleep(1)
            if Enzo_Stove.actual_status:
                Enzo_Stove.deactivate()
                while not do_webhooks_request('enzo_stove_pvpc_high'):
                    time.sleep(1)

        time.sleep(delay)
# Final line
