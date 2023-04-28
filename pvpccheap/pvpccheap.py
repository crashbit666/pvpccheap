
# This is a program that search the best hours to charge electric devices.
# Version: Beta 7
import datetime
import json
import time
import pytz
import logging
import logging.handlers
import firebase_admin
import mysql.connector
import bcrypt
import requests as requests
from mysql.connector import errorcode
from firebase_admin import credentials, db
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


"""
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
"""


class MariaDBHandler:
    def __init__(self, logger, user=secrets.get('DB_USER'), password=secrets.get('DB_PASSWORD'),
                 host=secrets.get('DB_HOST'), database=secrets.get('DB_NAME')):
        self.user = user
        self.password = password
        self.host = host
        self.database = database
        self.logger = logger

    def _connect(self):
        try:
            cnx = mysql.connector.connect(user=self.user, password=self.password, host=self.host,
                                          database=self.database)
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                self.logger.error("Something is wrong with your user name or password")
            elif err.errno == errorcode.ER_BAD_DB_ERROR:
                self.logger.error("Database does not exist")
            else:
                self.logger.error(err)
            raise
        return cnx

    def register_user(self, username, password):
        cnx = self._connect()
        cursor = cnx.cursor()
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_password))
            cnx.commit()
            self.logger.info("User %s registered successfully" % username)
        except mysql.connector.Error as err:
            self.logger.error("Error registering user %s: %s" % (username, str(err)))
            raise
        finally:
            cursor.close()
            cnx.close()

    def login_user(self, username, password):
        cnx = self._connect()
        cursor = cnx.cursor()
        cursor.execute("SELECT password FROM users WHERE username = %s", (username,))
        result = cursor.fetchone()
        cursor.close()
        cnx.close()

        if result:
            stored_password = result[0]
            if bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8')):
                self.logger.info("User %s logged in successfully" % username)
                return True
            else:
                self.logger.error("Invalid password for user %s" % username)
                return False
        else:
            self.logger.error("User %s not found" % username)
            return False

    def get_user_id(self, username):
        cnx = self._connect()
        cursor = cnx.cursor()
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        result = cursor.fetchone()
        cursor.close()
        cnx.close()

        if result:
            user_id = result[0]
            self.logger.debug("User ID for %s: %s" % (username, user_id))
            return user_id
        else:
            self.logger.error("User %s not found" % username)
            return None

    def get_device_settings(self, user_id, device_name):
        cnx = self._connect()
        cursor = cnx.cursor()
        cursor.execute("SELECT sleep_hours, sleep_hours_weekend, max_hours FROM device_settings WHERE user_id = %s AND "
                       "device_name = %s", (user_id, device_name))
        result = cursor.fetchone()
        cursor.close()
        cnx.close()

        if result:
            sleep_hours, sleep_hours_weekend, max_hours = result
            self.logger.debug("Sleep hours: %s, Sleep hours weekend: %s, Max hours: %s" % (sleep_hours,
                                                                                           sleep_hours_weekend,
                                                                                           max_hours))
            return sleep_hours, sleep_hours_weekend, max_hours
        else:
            return None, None, None


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
    def __init__(self, name, webhook_key, sleep_hours, sleep_hours_weekend, max_hours, logger, webhooks,
                 device_name, mariadb_handler):
        self.name = name
        self.webhook_key = webhook_key
        self.sleep_hours = sleep_hours
        self.sleep_hours_weekend = sleep_hours_weekend
        self.max_hours = max_hours
        self.actual_status = False
        self.logger = logger
        self.webhooks = webhooks
        self.device_name = device_name
        self._mariadb_handler = mariadb_handler

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

    @staticmethod
    def create_device(electric_price_checker, device_name, logger, webhooks, user_id, mariadb_handler):
        sleep_hours, sleep_hours_weekend, max_hours = mariadb_handler.get_device_settings(user_id, device_name)
        return Device(device_name, webhooks.webhook_key, sleep_hours, sleep_hours_weekend, max_hours, logger, webhooks,
                      device_name, mariadb_handler)


def update_cheap_hours(_electric_price_checker, device, _current_day, logger):
    try:
        return _electric_price_checker.get_best_hours(device.max_hours, _current_day)
    except ElectricPriceCheckerException as ex:
        logger.error("Error getting cheap hours: %s" % str(ex))
        return []


def is_in_cheap_hours(device, in_current_time):
    return in_current_time in device.cheap_hours


def register_user(mariadb_handler):
    print("Register a new user")
    username = input("Enter a username: ")
    password = input("Enter a password: ")
    try:
        mariadb_handler.register_user(username, password)
        print("User registered successfully")
    except Exception as e:
        print("Error registering user:", e)


def login_user(mariadb_handler, logger):
    username = input("Enter your username: ")
    cursor = mariadb_handler.cnx.cursor()
    cursor.execute("SELECT password FROM users WHERE username = %s", (username,))
    result = cursor.fetchone()
    cursor.close()

    if result:
        stored_password = result[0]
        password = input("Enter your password: ")
        if bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8')):
            logger.info("User %s logged in successfully" % username)
            return True
        else:
            logger.error("Invalid password for user %s" % username)
            return False
    else:
        logger.error("User %s not found" % username)
        return False


def login(mariadb_handler, logger):
    # User registration and login
    while True:
        print("Choose an option:")
        print("1. Register")
        print("2. Login")
        print("3. Exit")

        choice = input("Enter the number of your choice: ")

        if choice == "1":
            register_user(mariadb_handler)
        elif choice == "2":
            if login_user(mariadb_handler, logger):
                user_id = mariadb_handler.get_user_id(mariadb_handler)
                return user_id
            else:
                print("Invalid username or password")
        elif choice == "3":
            mariadb_handler.close_connection()
            return


def main():
    # Initialize logger
    logger = Logger()

    """
    # Initialize Firebase
    firebase_handler = FirebaseHandler(
        secrets.get('JSON_FILE'), secrets.get('FIREBASE_URL'), logger
    )
    """

    # Initialize MariaDB
    mariadb_handler = MariaDBHandler(logger)

    user_id = login(mariadb_handler, logger)

    # Initialize DateTimeHelper and ElectricPriceChecker
    electric_price_checker = ElectricPriceChecker(secrets, 'Europe/Madrid', logger)
    datetime_helper = DateTimeHelper('Europe/Madrid', logger)

    # Initialize webhooks
    webhooks = Webhooks(secrets.get('WEBHOOKS_KEY'))

    # Initialize devices
    devices = [
        Device.create_device("Scooter", logger, webhooks, user_id, mariadb_handler),
        Device.create_device("Boiler", logger, webhooks, user_id, mariadb_handler),
        Device.create_device("Papas Stove", logger, webhooks, user_id, mariadb_handler),
        Device.create_device("Enzo Stove", logger, webhooks, user_id, mariadb_handler)
    ]

    # Initialize current_day, current_time and cheap_hours
    current_day, current_time, current_week_day = datetime_helper.get_dates()

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
            for device in devices:
                try:
                    device.cheap_hours = update_cheap_hours(electric_price_checker, device, current_day, logger)
                except ElectricPriceCheckerException as e:
                    logger.error("Error getting cheap hours: %s" % str(e))
                    continue

        for device in devices:
            is_cheap = is_in_cheap_hours(device, current_time)
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
