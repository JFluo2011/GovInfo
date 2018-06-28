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

COL = get_col(MONGODB_COLLECTION)
REDIS_CLIENT = get_redis_client()
COUNT = 0


def get_html(url, method='GET', params=None, data=None, headers=None, byte_=False):
    if headers is None:
        global HEADERS
        headers = copy.deepcopy(HEADERS)
    proxies = {'http': get_proxy(REDIS_CLIENT)}
    # proxies = None
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
        return False
    selector = etree.HTML(source)
    title = selector.xpath(r'//*[@id="activity-name"]/text()')[0]
    try:
        content = selector.xpath(r'//*[@id="js_content"]')[0].xpath('string(.)')
        item.update({'content': content, 'title': title})
    except Exception as err:
        logging.error(f'{url}: {err.__class__.__name__}: {str(err)}')
        return False
    else:
        insert_item(item)
        return True


def parse_page(url, name, origin, params, referer=''):
    global COL
    global HEADERS
    global COUNT
    headers = copy.deepcopy(HEADERS)
    headers.update({'Referer': referer})
    source = get_html(url, params=params, headers=headers)
    if source is None:
        return False

    exception = False
    result = True
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
        result = parse_info(item, link, referer=referer)
        COUNT += 1
        if COUNT % 100 == 0:
            print(f'count: {COUNT}')
        time.sleep(5)
    return not exception or result


def parse_pages(task):
    url = task['url']
    name = task['name']
    origin = task['origin']
    params = task['params']
    referer = task['referer']
    page_count = parse_page_count(url, params=params, referer=referer)
    if page_count is None:
        return False

    time.sleep(5)
    result = True
    for page in range(1, page_count+1):
        params.update({'page': page})
        result = parse_page(url, name, origin, params=params, referer=referer)
        # if parse_page(url, wx_info, params=params, referer=referer):
        #     break
        time.sleep(5)
    return result


def parse_page_count(url, params, referer=''):
    global HEADERS
    headers = copy.deepcopy(HEADERS)
    headers.update({'Referer': referer})
    source = get_html(url, params=params, headers=headers)
    if source is None:
        return
    total = re.findall(r'找到约(\d+)条结果|$', source)[0]
    if total == '':
        logging.warning(f'{url}: {params} get page count failed')
        return None
    else:
        total = int(total)
        page_count = total//10 if (total % 10 == 0) else (total//10 + 1)
        if page_count > 10:
            raise Exception(f'{url}: {params} page too more')
        return page_count


def parse():
    col = get_col('wxgzh_task')
    while True:
        task = col.find_one({'crawled': 0})
        if task is not None:
            parse_pages(task) and col.update({'_id': task['_id']}, {"$set": {'crawled': 1}})
        time.sleep(5)


def get_date(start_year=2012, start_month='08', start_day='01'):
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
        date_lst.append((f'{year}-{str_m1}-02', f'{year}-{str_m2}-01'))
    str_month = str(month) if month >= 10 else f"0{month}"
    str_day = str(day) if day >= 10 else f"0{day}"
    date_lst.append((f'{year}-{str_month}-02', f'{year}-{str_month}-{str_day}'))
    return list(reversed(date_lst))


def create_task():
    url = 'http://weixin.sogou.com/weixin'
    lst = [
        WXInfo(name='成都高新', wx_id='oIWsFtzdz_uTS1UC9PKpVWMvDyS4', origin='cdht_wx',
               referer=('http://weixin.sogou.com/weixin?type=2&ie=utf8&query=%E6%88%90%E9%83%BD%E9%AB%98%E6%96%B0&'
                        'tsn=5&ft={}&et={}&interation=&wxid=&usip=')),
        WXInfo(name='成都工业和信息化', wx_id='oIWsFt_3i5qYBzUSy7UK7vm3EjpA', origin='cdgyhxxh_wx',
               referer=('http://weixin.sogou.com/weixin?type=2&ie=utf8&query=%E6%88%90%E9%83%BD%E9%AB%98%E6%96%B0&'
                        'tsn=5&ft{}&et={}&interation=&wxid=&usip='))
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
        import pprint
        pprint.pprint(get_date())
        for ft, et in get_date():
            print(f'{wx_info.origin}:{ft}-{et}')
            params.update({'ft': ft, 'et': et})
            data = {
                'url': url,
                'name': wx_info.name,
                'unique_id': f'{wx_info.origin}:{ft}-{et}',
                'origin': wx_info.origin,
                'params': params,
                'referer': wx_info.referer.format(ft, et),
                'crawled': 0
            }
            col.insert(data)


def run():
    global COL
    COL.ensure_index("unique_id", unique=True)
    parse()


def main():
    global COUNT
    setup_log(logging.INFO, os.path.join(os.path.abspath('.'), '../logs', 'wxgzh.log'))
    parse()
    print(COUNT)


if __name__ == '__main__':
    main()
