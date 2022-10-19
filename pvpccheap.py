# This is a program that search the best hours to charge electric devices.
# Version: Beta 2
import datetime
import json
import time
from webhooks import do_webhooks_request
import requests as requests
from secrets import secrets


def get_best_hours(max_items, actual_date):
    token = secrets.get('TOKEN')
    url = secrets.get('URL')
    headers = {'Accept': 'application/json; application/vnd.esios-api-v2+json', 'Content-Type': 'application/json',
               'Host': 'api.esios.ree.es', 'Authorization': 'Token token=' + token}

    pkw = []
    hours = []

    response = requests.get(url + '?start_date=' + str(actual_date) + 'T00:00:00.000+02:00' + '&end_date='
                            + str(actual_date) + 'T23:00:00.000+02:00' + '&geo_ids[]=8741', headers=headers)

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
    return hours


def get_dates():
    return datetime.date.today(), int(datetime.datetime.now().strftime("%H")), datetime.date.today().weekday()


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


class ISwitch:

    def __init__(self, actual_status):
        self.actual_status = actual_status

    def activate(self):
        self.actual_status = True

    def deactivate(self):
        self.actual_status = False


# Start point
if __name__ == '__main__':

    # Instance class
    Scooter_Switch = ISwitch(False)
    Boiler_Switch = ISwitch(False)
    Papas_Stove = ISwitch(False)
    Enzo_Stove = ISwitch(False)

    do_webhooks_request('scooter_pvpc_high')
    do_webhooks_request('boiler_pvpc_high')
    do_webhooks_request('papas_stove_pvpc_high')
    do_webhooks_request('enzo_stove_pvpc_high')

    # Initialize current_day, current_time and cheap_hours
    max_hours = 6
    current_day, current_time, current_week_day = get_dates()
    cheap_hours = get_best_hours(max_hours, current_day)
    papas_sleep_hours = [0, 1, 2, 3, 4, 5, 6, 7, 19, 20, 21, 22, 23, 24]
    papas_sleep_hours_weekend = [0, 1, 2, 3, 4, 5, 6, 7, 13, 14, 15, 19, 20, 21, 22, 23, 24]
    enzo_sleep_hours = [0, 1, 2, 3, 4, 5, 6, 7, 19, 20, 21, 22, 23, 24]
    enzo_sleep_hours_weekend = [0, 1, 2, 3, 4, 5, 6, 7, 14, 15, 16, 19, 20, 21, 22, 23, 24]

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
                do_webhooks_request('scooter_pvpc_down')
            if not Boiler_Switch.actual_status:
                Boiler_Switch.activate()
                do_webhooks_request('boiler_pvpc_down')
            if not Papas_Stove.actual_status:
                if current_week_day < 5:
                    if current_time in papas_sleep_hours:
                        Papas_Stove.activate()
                        do_webhooks_request('papas_stove_pvpc_down')
                else:
                    if current_time in papas_sleep_hours_weekend:
                        Papas_Stove.activate()
                        do_webhooks_request('papas_stove_pvpc_down')
            if not Enzo_Stove.actual_status:
                if current_week_day < 5:
                    if current_time in enzo_sleep_hours:
                        Enzo_Stove.activate()
                        do_webhooks_request('enzo_stove_pvpc_down')
                else:
                    if current_time in enzo_sleep_hours_weekend:
                        Enzo_Stove.activate()
                        do_webhooks_request('enzo_stove_pvpc_down')

        else:
            if Scooter_Switch.actual_status:
                Scooter_Switch.deactivate()
                do_webhooks_request('scooter_pvpc_high')
            if Boiler_Switch.actual_status:
                Boiler_Switch.deactivate()
                do_webhooks_request('boiler_pvpc_high')
            if Papas_Stove.actual_status:
                Papas_Stove.deactivate()
                do_webhooks_request('papas_stove_pvpc_high')
            if Enzo_Stove.actual_status:
                Enzo_Stove.deactivate()
                do_webhooks_request('enzo_stove_pvpc_high')

        time.sleep(delay)
# Final line
