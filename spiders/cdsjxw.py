import time
import re
import os
import copy
import logging

import requests
from lxml import etree

from common.utils import get_col, setup_log, get_proxy, get_redis_client
from local_config import MONGODB_COLLECTION


HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'Host': 'www.cdgy.gov.cn',
    'Pragma': 'no-cache',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.87 Safari/537.36',
}

# COL = get_col(MONGODB_COLLECTION)
COL = get_col('cdsjxw')
REDIS_CLIENT = get_redis_client()
SESSION = requests.session()
COUNT = 0


def get_html(url, method='GET', params=None, data=None, headers=None, byte_=False):
    global SESSION
    # proxies = {'http': get_proxy(REDIS_CLIENT)}
    proxies = None
    try:
        r = SESSION.request(url=url, method=method, params=params, data=data, headers=headers, proxies=proxies)
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


def parse_info(item, url):
    global HEADERS
    headers = copy.deepcopy(HEADERS)
    source = get_html(url, headers=headers, byte_=True)
    if source is None:
        return
    selector = etree.HTML(source)
    try:
        content = selector.xpath(r'//div[@id="top"]')[0].xpath('string(.)')
        item.update({'content': content})
    except:
        try:
            content = selector.xpath(r'//div[@class="main-contshow"]')[0].xpath('string(.)')
            item.update({'content': content})
        except Exception as err:
            logging.error(f'{url}: {err.__class__.__name__}: {str(err)}')
    finally:
        insert_item(item)


def parse_page(url, referer=''):
    global COL
    global COUNT
    global HEADERS
    headers = copy.deepcopy(HEADERS)
    headers.update({'referer': referer})
    stop = False
    base_url = 'http://www.cdgy.gov.cn'
    source = get_html(url, headers=headers, byte_=True)
    if source is None:
        return False
    selector = etree.HTML(source)
    regex = '//div[@class="newlist_left_cont"]/ul'
    for sel in selector.xpath(regex):
        link = base_url + sel.xpath(r'li[1]/a/@href')[0]
        if COL.find_one({'url': link}):
            stop = True
            logging.warning(f'{link} is download already')
            continue
        text = sel.xpath(r'li[2]/text()')[0]
        text = ''.join(text.split())
        text = re.sub(r'\s|:|：', '', text)
        promulgator, date = re.findall(r'来源(.*?)发布时间(\d{4}-\d{2}-\d{2})', text)[0]
        item = {
            'url': link,
            'unique_id': link,
            'title': sel.xpath(r'li[1]/a/@title')[0],
            'summary': '',
            'source': promulgator,
            'date': date,
            'origin': 'cdsjxw',
            'type': 'web'
        }
        parse_info(item, link)
        COUNT += 1
        if COUNT % 100 == 0:
            print(f'count: {COUNT}')
        time.sleep(2)
    return stop


def parse_pages(page_count):
    parse_page('http://www.cdgy.gov.cn/cdsjxw/c132946/zwxx.shtml')
    referer = 'http://www.cdgy.gov.cn/cdsjxw/c132946/zwxx.shtml'
    base_url = 'http://www.cdgy.gov.cn/cdsjxw/c132946/zwxx_{}.shtml'
    for i in range(2, page_count+1):
        url = base_url.format(i)
        parse_page(url, referer=referer)
        # if parse_page(url, referer=referer):
        #     break
        referer = url
        time.sleep(3)


def parse_page_count(url):
    global HEADERS
    headers = copy.deepcopy(HEADERS)
    source = get_html(url=url, headers=headers)
    if source is None:
        return
    page_count = re.findall(r'createPageHTML\(\'page_div\',(\d+),.*?\)|$', source)[0]
    if page_count == '':
        raise Exception('get page count failed')
    else:
        return int(page_count)


def run(url):
    global COL
    COL.ensure_index("unique_id", unique=True)
    page_count = parse_page_count(url)
    time.sleep(3)
    parse_pages(page_count)


def main():
    setup_log(logging.INFO, os.path.join(os.path.abspath('.'), '../logs', 'cdsjxw.log'))
    url = 'http://www.cdgy.gov.cn/cdsjxw/c132946/zwxx.shtml'
    run(url)


if __name__ == '__main__':
    main()
