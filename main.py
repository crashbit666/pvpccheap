# This is a program that search the best hours to charge electric devices.
import json
import requests as requests
import datetime
from secrets import secrets

status = bool


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


def check_status():
    # Here we need to check if past hour is expensive or cheap hour. If the hour is not cheap, the last status
    # will be False
    current_day = datetime.date.today().strftime("%d")
    current_time = datetime.datetime.now().strftime("%H")
    best_hours = get_best_hours(7)

    ''' Debug'''
    print("dia actual ---->", current_day)
    print("hora actual --->", current_time)
    print("millors hores ->", best_hours)
    ''''''

    if current_time in best_hours:
        return True
    else:
        return False


class ISwitch:

    def __init__(self, new_status):
        self.actual_status = check_status()
        self.new_status = new_status

    def activate(self):
        self.actual_status = True

    def deactivate(self):
        self.actual_status = False


# Start point
if __name__ == '__main__':
    Switch = ISwitch(True) # We need to add/get var to remember status of switch first time run
    print(Switch.actual_status)

# Final line
