import requests

from secrets import secrets


def do_webhooks_request(pvpc):
    requests.post('https://maker.ifttt.com/trigger/'+pvpc+'/with/key/'+secrets.get('WEBHOOKS_KEY'))
