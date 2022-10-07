# This is a program that search the best hours to charge electric devices.
import datetime
import json
import time
from webhooks import do_webhooks_request
import requests as requests
from secrets import secrets


def get_best_hours(max_items):
    token = secrets.get('TOKEN')
    url = secrets.get('URL')
    headers = {'Accept': 'application/json; application/vnd.esios-api-v2+json', 'Content-Type': 'application/json',
               'Host': 'api.esios.ree.es', 'Authorization': 'Token token=' + token}

    pkw = []
    hours = []

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        json_data = json.loads(response.text)
        vals = json_data['indicator']['values']
        prices = [x['value'] for x in vals]
        hour = 0
        x = 0
        for price in prices:
            if vals[x].get('geo_id') == 8741:
                pkw.append(round(price / 1000, 4))
                hour += 1
            x += 1
    else:
        pkw = "Error connecting to database"

    # Next four lines format ESIOS data. Enumerate data for hours, sort and remove price.
    pkw = sorted(list(enumerate(pkw)), key=lambda k: k[1])[0:max_items]
    for i in pkw:
        hours.append(i[0])
    return hours


def get_dates():
    return int(datetime.date.today().strftime("%d")), int(datetime.datetime.now().strftime("%H"))


def cheap_price():
    # Here we need to check if past hour is expensive or cheap hour. If the hour is not cheap, the last status
    # will be False
    current_day, current_time = get_dates()
    best_hours = get_best_hours(7)

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

    def __init__(self, actual_status, new_status):
        self.actual_status = actual_status
        self.new_status = new_status

    def activate(self):
        print('Activating ...')
        self.actual_status = True

    def deactivate(self):
        print('Deactivating ...')
        self.actual_status = False


# Start point
if __name__ == '__main__':

    # Instance class
    Scooter_Switch = ISwitch(False, False)

    # Infinite loop
    while True:
        print('-----------------------------------')
        delay = 60 * delay_to_oclock()  # delay until oclock

        if cheap_price():
            if not Scooter_Switch.actual_status:
                Scooter_Switch.activate()
                do_webhooks_request('pvpc_down')
        else:
            if Scooter_Switch.actual_status:
                Scooter_Switch.deactivate()
                do_webhooks_request('pvpc_high')

        time.sleep(delay)

        '''
        if check_status() and not Scooter_Switch.actual_status:
            Scooter_Switch.activate()
            do_webhooks_request('pvpc_down')
        elif not check_status() and Scooter_Switch.actual_status:
            Scooter_Switch.deactivate()
            do_webhooks_request('pvpc_high')
        time.sleep(delay)
        '''

# Final line
