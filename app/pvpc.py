# This program is free software: you can redistribute it and/or modify
# This is an API for pvpccheap program
import pytz
import datetime
import json
import requests as requests
import logging
import logging.handlers
import time

from app.api_secrets import apisecrets
from flask import Flask
from flask_restful import Api


app = Flask(__name__)
api = Api(app)


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


class ElectricPriceChecker:
    def __init__(self, _secrets, timezone, logger):
        self.token = _secrets.get('TOKEN')
        self.url = _secrets.get('URL')
        self.timezone = timezone
        self.logger = logger

    def get_best_hours(self, actual_date):
        local_timezone = pytz.timezone(self.timezone)
        start_date = local_timezone.localize(datetime.datetime.combine(actual_date, datetime.time(0, 0, 0)),
                                             is_dst=None).isoformat()
        end_date = local_timezone.localize(datetime.datetime.combine(actual_date, datetime.time(23, 0, 0)),
                                           is_dst=None).isoformat()

        headers = {'Accept': 'application/json; application/vnd.esios-app-v2+json', 'Content-Type': 'application/json',
                   'Host': 'app.esios.ree.es', 'x-app-key': self.token}

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
        pkw = sorted(list(enumerate(pkw)), key=lambda k: k[1])
        for i in pkw:
            hours.append(i[0])

        self.logger.debug("Best hours: %s" % hours)
        return hours

    @staticmethod
    def update_cheap_hours(current_day, logger):
        try:
            return ElectricPriceChecker.get_best_hours(current_day, logger)
        except ElectricPriceCheckerException as ex:
            logger.error("Error getting cheap hours: %s" % str(ex))
            return []


class ElectricPriceCheckerException(Exception):
    pass


class Webhooks:
    def __init__(self, webhook_apikey=apisecrets.get('WEBHOOK_APIKEY')):
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


class DateTimeHelper:
    def __init__(self, timezone, logger):
        self.timezone = timezone
        self.logger = logger

    def get_dates(self):
        local_timezone = pytz.timezone(self.timezone)
        local_dt = datetime.datetime.now(local_timezone)
        self.logger.info("Hour: %s, Date: %s, Weekday: %s" % (local_dt.hour, local_dt.date(), local_dt.weekday()))
        return local_dt.date(), local_dt.hour, local_dt.weekday()
