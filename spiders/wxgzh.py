import datetime
import time
import re
import os
import copy
import logging
from collections import namedtuple

import requests
from lxml import etree
from pymongo.errors import DuplicateKeyError

from common.utils import get_col, setup_log, get_proxy, get_redis_client
from local_config import MONGODB_COLLECTION

WXInfo = namedtuple('WXInfo', ['name', 'wx_id', 'origin', 'referer'])

HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'Host': 'weixin.sogou.com',
    'Pragma': 'no-cache',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.87 Safari/537.36',
}
SESSION = requests.session()

COL = get_col(MONGODB_COLLECTION)
REDIS_CLIENT = get_redis_client()
COUNT = 0


def get_html(url, method='GET', params=None, data=None, headers=None, proxies=None, byte_=False):
    if headers is None:
        global HEADERS
        headers = copy.deepcopy(HEADERS)
    # proxies = None
    try:
        r = requests.request(url=url, method=method, params=params,
                             data=data, headers=headers, proxies=proxies, timeout=10)
    except Exception as err:
        logging.error(f'{url}: {params} download error, {err.__class__.__name__}: {str(err)}')
        return None
    if 'ip-time-p' in r.text:
        logging.error(f'{url}: {params} download error, ip-time-p proxies: {proxies}')
        return None
    if byte_:
        return r.content
    else:
        return r.text


def insert_item(item):
    global COL
    COL.insert(item)


def parse_info(item, url, referer=''):
    global HEADERS
    headers = copy.deepcopy(HEADERS)
    # headers.update({'Referer': referer, 'Host': 'mp.weixin.qq.com'})
    headers.update({'Host': 'mp.weixin.qq.com'})
    source = get_html(url, headers=headers)
    if source is None:
        return -1
    selector = etree.HTML(source)
    try:
        title = selector.xpath(r'//*[@id="activity-name"]/text()')[0]
        content = selector.xpath(r'//*[@id="js_content"]')[0].xpath('string(.)')
        item.update({'content': content, 'title': title})
    except Exception as err:
        logging.error(f'{url}: {err.__class__.__name__}: {str(err)}')
        return -1
    else:
        insert_item(item)
        return 1


def parse_page(task):
    global COL
    global HEADERS
    global COUNT
    url = task['url']
    name = task['name']
    origin = task['origin']
    params = task['params']
    referer = task['referer']
    headers = copy.deepcopy(HEADERS)
    headers.update({'Referer': referer})
    proxies = {'http': get_proxy(REDIS_CLIENT)}
    source = get_html(url, params=params, headers=headers, proxies=proxies)
    if source is None:
        return -1

    exception = False
    result = 1
    total = re.findall(r'找到约(\d+)条结果|$', source)[0]
    if total != '' and int(total) > 10:
        logging.error(f'{url}: {params} page too more')
        return -1
    selector = etree.HTML(source)
    for sel in selector.xpath(r'//li[contains(@id, "sogou_vr_")]'):
        unique_id = sel.xpath(r'./@d')[0]
        link = sel.xpath(r'div/h3/a/@href')[0]
        if COL.find_one({'unique_id': unique_id}):
            logging.warning(f'{link} is download already')
            continue
        try:
            if sel.xpath(r'div/div/a/text()')[0] != name:
                logging.warning(f'{url}: {params}\n{link}: is not publish from {name}')
                continue
            item = {
                'url': link,
                'unique_id': unique_id,
                'summary': sel.xpath(r'./div/p[@class="txt-info"]')[0].xpath('string(.)'),
                'date': time.strftime("%Y-%m-%d", time.localtime(int(sel.xpath(r'div/div/@t')[0]))),
                'source': sel.xpath(r'div/div/a/text()')[0],
                'origin': origin,
                'type': 'wxgzh',
            }
        except Exception as err:
            exception = True
            logging.error(f'{url}: {params}\n{link}:{err.__class__.__name__}: {str(err)}')
            continue
        res = parse_info(item, link, referer=referer)
        if result == 1:
            result = res
        time.sleep(5)
    if exception:
        return -1
    else:
        return result


def parse():
    col = get_col('wxgzh_task')
    while True:
        task = col.find_one_and_update({'crawled': 0}, {'$set': {'crawled': 2}})
        if task is not None:
            logging.info(f'{task} start')
            result = parse_page(task)
            col.update({'_id': task['_id']}, {"$set": {'crawled': result}})
            logging.info(f'{task} done, result: {result}')
        time.sleep(10)


def create_task():
    url = 'http://weixin.sogou.com/weixin'
    lst = [
        WXInfo(name='成都高新', wx_id='oIWsFtzdz_uTS1UC9PKpVWMvDyS4', origin='cdht_wx',
               referer=('http://weixin.sogou.com/weixin?type=2&ie=utf8&query=%E6%88%90%E9%83%BD%E9%AB%98%E6%96%B0'
                        '&tsn=0&ft=&et=&interation=&wxid=oIWsFtzdz_uTS1UC9PKpVWMvDyS4'
                        '&usip=%E6%88%90%E9%83%BD%E9%AB%98%E6%96%B0')),
        WXInfo(name='成都工业和信息化', wx_id='oIWsFt_3i5qYBzUSy7UK7vm3EjpA', origin='cdgyhxxh_wx',
               referer=('http://weixin.sogou.com/weixin?type=2&ie=utf8'
                        '&query=%E6%88%90%E9%83%BD%E5%B7%A5%E4%B8%9A%E5%92%8C%E4%BF%A1%E6%81%AF%E5%8C%96'
                        '&tsn=0&ft=&et=&interation=&wxid=oIWsFt_3i5qYBzUSy7UK7vm3EjpA'
                        '&usip=%E6%88%90%E9%83%BD%E5%B7%A5%E4%B8%9A%E5%92%8C%E4%BF%A1%E6%81%AF%E5%8C%96')),
        WXInfo(name='企邦帮', wx_id='oIWsFt5bBYFhqeLQbPdiR_BYnIo0', origin='qbb_wx',
               referer=('http://weixin.sogou.com/weixin?type=2&ie=utf8&query=%E4%BC%81%E9%82%A6%E5%B8%AE&tsn=0'
                        '&ft=&et=&interation=&wxid=oIWsFt5bBYFhqeLQbPdiR_BYnIo0&usip=%E4%BC%81%E9%82%A6%E5%B8%AE'))
    ]
    for wx_info in lst:
        params = {
            'type': '2',
            'ie': 'utf8',
            'query': wx_info.name,
            'tsn': '5',
            'interation': '',
            'wxid': wx_info.wx_id,
            'usip': wx_info.name,
        }
        col = get_col('wxgzh_task')
        col.ensure_index("unique_id", unique=True)
        date = datetime.datetime.now()
        # days = int((datetime.datetime.now() - datetime.datetime.strptime('2012-08-01', '%Y-%m-%d')).days)
        days = int((datetime.datetime.now() - datetime.datetime.strptime('2015-01-01', '%Y-%m-%d')).days)
        while days >= 0:
            t = date.strftime("%Y-%m-%d")
            data = {
                'url': url,
                'name': wx_info.name,
                'unique_id': f'{wx_info.origin}-{t}',
                'origin': wx_info.origin,
                'params': params,
                'referer': wx_info.referer,
                'crawled': 0
            }
            date -= datetime.timedelta(days=1)
            days -= 1
            params.update({'ft': t, 'et': t})
            try:
                col.insert(data)
            except DuplicateKeyError:
                # logging.warning(f'task unique_id {wx_info.origin}-{t} already exists')
                pass


def run():
    global COL
    COL.ensure_index("unique_id", unique=True)
    parse()


def main():
    global COUNT
    setup_log(logging.INFO, os.path.join(os.path.abspath('.'), '../logs', 'wxgzh.log'))
    # create_task()
    parse()
    print(COUNT)


if __name__ == '__main__':
    main()
