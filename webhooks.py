import time
import requests
from secrets import secrets


def do_webhooks_request(pvpc):
    try:
        requests.post('https://maker.ifttt.com/trigger/'+pvpc+'/with/key/'+secrets.get('WEBHOOKS_KEY'))
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
