import time
import re
import os
import copy
import logging
from collections import namedtuple

import requests
from lxml import etree

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

# COL = get_col(MONGODB_COLLECTION)
COL = get_col('test')
REDIS_CLIENT = get_redis_client()


def get_html(url, method='GET', params=None, data=None, headers=None, byte_=False):
    if headers is None:
        global HEADERS
        headers = copy.deepcopy(HEADERS)
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


def insert_item(item):
    global COL
    COL.insert(item)


def parse_info(item, url, referer=''):
    global HEADERS
    headers = copy.deepcopy(HEADERS)
    headers.update({'Referer': referer, 'Host': 'mp.weixin.qq.com'})
    source = get_html(url, headers=headers)
    if source is None:
        return
    selector = etree.HTML(source)
    title = selector.xpath(r'//*[@id="activity-name"]/text()')[0]
    try:
        content = selector.xpath(r'//*[@id="js_content"]')[0].xpath('string(.)')
        item.update({'content': content, 'title': title})
    except Exception as err:
        logging.error(f'{url}: {err.__class__.__name__}: {str(err)}')
    finally:
        insert_item(item)


def parse_page(url, params, origin, referer=''):
    global COL
    global HEADERS
    count = 0
    stop = False
    headers = copy.deepcopy(HEADERS)
    headers.update({'Referer': referer})
    source = get_html(url, params=params, headers=headers)
    if source is None:
        return False
    selector = etree.HTML(source)
    for sel in selector.xpath(r'//div[@class="txt-box"]'):
        link = sel.xpath(r'h3/a/@href')[0]
        signature = re.findall(r'signature=(.{64})', link)[0]
        if COL.find_one({'url': signature}):
            stop = True
            logging.warning(f'{link} is download already')
            continue
        try:
            item = {
                'url': signature,
                'date': time.strftime("%Y-%m-%d", time.localtime(int(sel.xpath(r'div/@t')[0]))),
                'promulgator': sel.xpath(r'div/a/text()')[0],
                'origin': origin,
            }
        except Exception as err:
            logging.error(f'{url}: {err.__class__.__name__}: {str(err)}')
            continue
        parse_info(item, link, referer=referer)
        count += 1
        # if count % 100 == 0:
        #     print(f'count: {count}')
        time.sleep(5)
    return stop


def parse_pages(url, params, origin, referer=''):
    page_count = parse_page_count(url, params=params, referer=referer)
    time.sleep(5)
    for page in range(1, page_count+1):
        params.update({'page': page})
        if parse_page(url, params=params, origin=origin, referer=referer):
            break
        time.sleep(5)


def parse_page_count(url, params, referer=''):
    global HEADERS
    headers = copy.deepcopy(HEADERS)
    headers.update({'Referer': referer})
    source = get_html(url, params=params, headers=headers)
    if source is None:
        return
    page_count = re.findall(r'找到约(\d+)条结果|$', source)[0]
    if page_count == '':
        raise Exception('get page count failed')
    else:
        return int(page_count)


def parse(url, params, origin, referer=''):
    # 'ft': '2018-04-27',
    # 'et': '2018-05-27',
    for ft, et in get_date():
        params.update({'ft': ft, 'et': et})
        referer = referer.format(ft, et)
        parse_pages(url, params, origin=origin, referer=referer)
        time.sleep(5)


def get_date(start_year=2012, start_month='08', start_day='01'):
    time.strftime("%Y-%m-%d", time.localtime())
    now = time.localtime()
    year, month, day = now.tm_year, now.tm_mon, now.tm_mday
    date_lst = [(f'{start_year}-{start_month}-{start_day}', f'{start_year+1}-01-01')]
    for y in range(start_year+1, year):
        for m in range(1, 12):
            str_m1 = str(m) if m >= 10 else f'0{m}'
            str_m2 = str(m+1) if (m+1) >= 10 else f'0{m+1}'
            date_lst.append((f'{y}-{str_m1}-02', f'{y}-{str_m2}-01'))
        date_lst.append((f'{y}-{12}-02', f'{y+1}-01-01'))
    for m in range(1, month):
        str_m1 = str(m) if m >= 10 else f'0{m}'
        str_m2 = str(m + 1) if (m + 1) >= 10 else f'0{m+1}'
        date_lst.append((f'{y}-{str_m1}-02', f'{y}-{str_m2}-01'))
    str_month = str(month) if month >= 10 else f"0{month}"
    str_day = str(day) if day >= 10 else f"0{day}"
    date_lst.append((f'{year}-{str_month}-02', f'{year}-{str_month}-{str_day}'))
    return list(reversed(date_lst))


def run(url, wx_info):
    global COL
    COL.ensure_index("url", unique=True)
    params = {
        'type': '2',
        'ie': 'utf8',
        'query': wx_info.name,
        'tsn': '5',
        'interation': '',
        'wxid': wx_info.wx_id,
        'usip': wx_info.name,
    }
    parse(url, params, origin=wx_info.origin, referer=wx_info.referer)


def main():
    setup_log(logging.INFO, os.path.join(os.path.abspath('.'), '../logs', 'cdht.log'))
    lst = [
        WXInfo(name='成都高新', wx_id='oIWsFtzdz_uTS1UC9PKpVWMvDyS4', origin='cdhtwx',
               referer=('http://weixin.sogou.com/weixin?type=2&ie=utf8&query=%E6%88%90%E9%83%BD%E9%AB%98%E6%96%B0&'
                        'tsn=5&ft={}&et={}&interation=&wxid=&usip=')),
        # WXInfo(name='成都高新', wx_id='oIWsFtzdz_uTS1UC9PKpVWMvDyS4',
        #        referer=('http://weixin.sogou.com/weixin?type=2&ie=utf8&query=%E6%88%90%E9%83%BD%E9%AB%98%E6%96%B0&'
        #                 'tsn=5&ft=2018-04-27&et=2018-05-27&interation=&wxid=&usip='))
    ]
    for wx_info in lst:
        url = 'http://weixin.sogou.com/weixin'
        run(url, wx_info)


if __name__ == '__main__':
    main()
