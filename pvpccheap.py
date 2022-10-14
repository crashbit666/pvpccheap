# This is a program that search the best hours to charge electric devices.
# Version: Beta 2
import datetime
import json
import time
from webhooks import do_webhooks_request
import requests as requests
from secrets import secrets


def get_best_hours(max_items, adate):
    token = secrets.get('TOKEN')
    url = secrets.get('URL')
    headers = {'Accept': 'application/json; application/vnd.esios-api-v2+json', 'Content-Type': 'application/json',
               'Host': 'api.esios.ree.es', 'Authorization': 'Token token=' + token}

    pkw = []
    hours = []

    response = requests.get(url+'?start_date='+str(adate)+'T00:00:00.000+02:00'+'&end_date='+str(adate)
                            + 'T23:00:00.000+02:00' + '&geo_ids[]=8741', headers=headers)

    if response.status_code == 200:
        json_data = json.loads(response.text)
        print(json_data)
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
    return datetime.date.today(), int(datetime.datetime.now().strftime("%H"))


def cheap_price(last_day_check_in, first_best_hours):
    # Here we need to check if past hour is expensive or cheap hour. If the hour is not cheap, the last status
    # will be False
    current_day, current_time = get_dates()

    if last_day_check_in != current_day or first_best_hours is None:
        best_hours = get_best_hours(7, current_day)

    ''''''
    print("current_day ---->", current_day)
    print("current_day ---->", type(current_day))

    print("current_time --->", current_time)
    print("current_time --->", type(current_time))

    print("best_hours ----->", best_hours)
    print("best_hours ----->", type(best_hours))
    ''''''

    if current_time in best_hours:
        print('cheap_price = True')
        return True
    else:
        print('cheap_price = False')
        return False


def delay_to_oclock():
    minutes = int(datetime.datetime.now().strftime("%M"))
    print('minutes = '+str(minutes))
    print('delay_to_oclock = ' + str(int(60 - minutes)))
    return 60 - minutes


class ISwitch:

    def __init__(self, actual_status):
        self.actual_status = actual_status

    def activate(self):
        print('Activating ...')
        self.actual_status = True

    def deactivate(self):
        print('Deactivating ...')
        self.actual_status = False


# Start point
if __name__ == '__main__':

    # Instance class
    Scooter_Switch = ISwitch(False)
    Boiler_Switch = ISwitch(False)
    best_hours = None

    # Infinite loop
    while True:
        print('-----------------------------------')
        delay = 60 * delay_to_oclock()  # get delay time until o'clock

        last_day_check = get_dates()[0]

        if cheap_price(last_day_check, best_hours):
            if not Scooter_Switch.actual_status:
                print('Aactivant....')
                Scooter_Switch.activate()
                do_webhooks_request('scooter_pvpc_down')
            if not Boiler_Switch.actual_status:
                Boiler_Switch.activate()
                do_webhooks_request('boiler_pvpc_down')
        else:
            if Scooter_Switch.actual_status:
                print('Desactivant...')
                Scooter_Switch.deactivate()
                do_webhooks_request('scooter_pvpc_high')
            if Boiler_Switch.actual_status:
                Boiler_Switch.deactivate()
                do_webhooks_request('boiler_pvpc_high')

        time.sleep(delay)
# Final line
