import os
import logging
import random
from logging.handlers import RotatingFileHandler

import redis

from common.mongodb_client import MongodbClient
from local_config import MONGODB_DB, MONGODB_PORT, MONGODB_SERVER
from local_config import REDIS_DB, REDIS_PORT, REDIS_SERVER


FORMAT = '%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s'
DATEFMT = '%a, %d %b %Y %H:%M:%S'


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
    return proxy


def get_redis_client():
    return redis.Redis(host=REDIS_SERVER, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
