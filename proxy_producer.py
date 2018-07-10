import os
import time
import json
import logging
from concurrent.futures import ThreadPoolExecutor

import requests

from gov_info.common.local_config import proxies_urls
from gov_info.common.utils import get_redis_client, setup_log


def insert_redis(redis_client, ip, ttl):
    key = 'http://{}'
    retry = 3

    while retry > 0:
        try:
            redis_client.set(name=key.format(ip), value=key.format(ip), px=ttl)
        except Exception as err:
            logging.error(str(err))
            continue
        else:
            return True
    else:
        return False


def get_proxies(url):
    redis_client = get_redis_client()
    while True:
        try:
            r = requests.get(url, timeout=10)
        except Exception as err:
            logging.error(str(err))
            continue
        if r.status_code == 200:
            if 'msg' in r.text:
                logging.info('{} {}'.format(url, json.loads(r.text)['msg']))
                break
            ips = r.text.strip('\n').split('\n')
            for ip in ips:
                if not insert_redis(redis_client, *ip.split(',')):
                    break

        time.sleep(10)
    else:
        logging.info('thread close')


def main():
    setup_log(logging.INFO, os.path.join(os.path.abspath('.'), 'logs', 'proxy_producer.log'))
    with ThreadPoolExecutor(max_workers=len(proxies_urls)) as executor:
        executor.map(get_proxies, proxies_urls)


if __name__ == '__main__':
    main()
