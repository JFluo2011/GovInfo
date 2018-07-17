import os
import logging
import random
import hashlib
from collections import namedtuple
from logging.handlers import RotatingFileHandler

import redis
import requests

from gov_info.common.mongodb_client import MongodbClient
from gov_info.common.config import MONGODB_DB, MONGODB_PORT, MONGODB_SERVER
from gov_info.common.config import USER_REDIS


FORMAT = '%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s'
DATEFMT = '%a, %d %b %Y %H:%M:%S'

WXInfo = namedtuple('WXInfo', ['name', 'wx_id', 'origin', 'referer', 'location', 'tag'])


class MyRFPDupeFilter(object):
    def __init__(self, server, key, debug=False):
        pass

    @classmethod
    def from_settings(cls, settings):
        pass

    @classmethod
    def from_crawler(cls, crawler):
        pass

    def request_seen(self, request):
        pass

    def request_fingerprint(self, request):
        pass

    def close(self, reason=''):
        pass

    def clear(self):
        pass

    def log(self, request, spider):
        pass


def get_md5(txt):
    m = hashlib.md5()
    m.update(txt.encode('utf-8'))
    return m.hexdigest()


def get_col(col_name):
    mongodb_client = MongodbClient(address=MONGODB_SERVER, port=MONGODB_PORT)
    db = mongodb_client.get_database(MONGODB_DB)
    return mongodb_client.get_collection(db, col_name)


def setup_log(level, file_path, max_bytes=20 * 1024 * 1024, backup_count=5):
    if not os.path.exists(os.path.split(file_path)[0]):
        os.makedirs(os.path.split(file_path)[0])
    logging.basicConfig(level=level,
                        format=FORMAT,
                        datefmt=DATEFMT)
    rotate_handler = RotatingFileHandler(file_path, maxBytes=max_bytes, backupCount=backup_count)
    rotate_handler.setLevel(level)
    rotate_handler.setFormatter(logging.Formatter(FORMAT, DATEFMT))
    logging.getLogger('').addHandler(rotate_handler)


def get_proxy(redis_client):
    try:
        proxy = random.choice(redis_client.keys('http://*'))
    except:
        return None
    return proxy.decode('utf-8')


def get_redis_client():
    return redis.StrictRedis(**USER_REDIS)


def get_html(url, method='GET', params=None, data=None, headers=None, byte_=False):
    # proxies = {'http': get_proxy(REDIS_CLIENT)}
    proxies = None
    try:
        r = requests.request(url=url, method=method, params=params, data=data, headers=headers, proxies=proxies)
    except Exception as err:
        logging.error(f'{url}: download error, {err.__class__.__name__}: {str(err)}')
        return None
    if byte_:
        return r.content
    else:
        return r.text
