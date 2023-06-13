import datetime
import json
import time

import pytz
import requests
from app.api_secrets import apisecrets


class ElectricPriceChecker:
    def __init__(self, _secrets, timezone):
        self.token = _secrets.get('TOKEN')
        self.url = _secrets.get('URL')
        self.timezone = timezone

    def get_best_hours(self, actual_date):
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
            print(f"Error connecting to ESIOS API. Status code: {response.status_code}, Response: {response.text}")
            raise ElectricPriceCheckerException("Error connecting to ESIOS API.")

        # Next four lines format ESIOS data. Enumerate data for hours, sort and remove price.
        pkw = sorted(list(enumerate(pkw)), key=lambda k: k[1])
        for i in pkw:
            hours.append(i[0])

        return hours


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
