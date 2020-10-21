#!/usr/bin/python

import json
import logging as log
import os
import sys
import time

import requests
import tldextract

API = 'https://api.cloudflare.com/client/v4/'

log.basicConfig(
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=log.INFO
)

TOKEN = os.environ['TOKEN']
DOMAIN = tldextract.extract(os.environ['DOMAIN'])
HEADERS = {'Authorization': 'Bearer ' + TOKEN, 'Content-Type': 'application/json'}

SLEEP_INTERVAL_SEC = 300


class Ddclient:
    ip = ''
    domain = ''
    subdomain = ''
    full_domain = ''

    def __init__(self):
        if DOMAIN.domain != '' and DOMAIN.suffix != '':
            self.domain = '{}.{}'.format(DOMAIN.domain, DOMAIN.suffix)
            if DOMAIN.subdomain != '':
                self.subdomain = DOMAIN.subdomain
                self.full_domain = '{}.{}'.format(DOMAIN.subdomain, self.domain)
            else:
                # No subdomain is described with an @
                self.subdomain = '@'
                self.full_domain = self.domain
        else:
            log.error('Invalid domain: {}'.format(DOMAIN))
            sys.exit(1)

        if self.check_token():
            zone_id = self.get_zone()
            record_id = self.get_record(zone_id)

            try:
                running = True
                while running:
                    self.update(zone_id, record_id)
                    time.sleep(SLEEP_INTERVAL_SEC)
            except KeyboardInterrupt:
                sys.exit(0)

    def update(self, zone_id, record_id):
        ip = self.get_ip()
        if self.ip != ip:
            self.ip = ip
            self.update_record(zone_id, record_id)

    def check_token(self):
        response = requests.get(API + 'user/tokens/verify', headers=HEADERS)
        if response.status_code == 200:
            try:
                r = json.loads(response.text)
                if r['success']:
                    return True
                else:
                    log.error('Token invalid')
                    return False
            except json.decoder.JSONDecodeError:
                log.error('Token invalid')
                return False
        else:
            log.error('Token invalid')
            return False

    def get_ip(self):
        return requests.get('https://ipinfo.io/ip').text.strip('\n')

    def get_zone(self):
        response = json.loads(requests.get(API + 'zones?', params={'name': self.domain}, headers=HEADERS).text)
        for result in response['result']:
            if result['name'] == self.domain:
                return result['id']

    def get_record(self, zone_id):
        response = json.loads(requests.get(API + 'zones/' + zone_id + '/dns_records', params={'name': self.full_domain},
                                           headers=HEADERS).text)
        for result in response['result']:
            if result['name'] == self.full_domain:
                return result['id']

    def update_record(self, zone_id, record_id):
        log.info('Updating dns record: {} with ip: {}'.format(self.full_domain, self.ip))
        requests.put('{}zones/{}/dns_records/{}'.format(API, zone_id, record_id),
                     data=json.dumps({'type': 'A', 'name': self.full_domain, 'content': self.ip}), headers=HEADERS)


if __name__ == '__main__':
    Ddclient()
