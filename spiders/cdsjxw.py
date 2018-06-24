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

COL = get_col(MONGODB_COLLECTION)
# COL = get_col('test')
REDIS_CLIENT = get_redis_client()
SESSION = requests.session()


def get_html(url, referer='', byte_=False):
    global HEADERS
    headers = copy.deepcopy(HEADERS)
    if referer != '':
        headers.update({'Referer': referer})
    # proxies = {'http': get_proxy(REDIS_CLIENT)}
    proxies = None
    try:
        r = SESSION.get(url, headers=headers, proxies=proxies)
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
    source = get_html(url, byte_=True)
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
    count = 0
    base_url = 'http://www.cdgy.gov.cn'
    source = get_html(url, referer=referer, byte_=True)
    if source is None:
        return
    selector = etree.HTML(source)
    regex = '//div[@class="newlist_left_cont"]/ul'
    for sel in selector.xpath(regex):
        link = base_url + sel.xpath(r'li[1]/a/@href')[0]
        if COL.find_one({'url': link}):
            logging.warning(f'{link} is download already')
            continue
        text = sel.xpath(r'li[2]/text()')[0]
        text = ''.join(text.split())
        text = re.sub(r'\s|:|：', '', text)
        promulgator, date = re.findall(r'来源(.*?)发布时间(\d{4}-\d{2}-\d{2})', text)[0]
        item = {
            'url': link,
            'title': sel.xpath(r'li[1]/a/@title')[0],
            'promulgator': promulgator,
            'date': date,
            'origin': 'cdsjxw',
        }
        parse_info(item, link)
        if count % 100:
            print(f'count: {count}')
        time.sleep(2)


def parse_pages(page_count):
    parse_page('http://www.cdgy.gov.cn/cdsjxw/c132946/zwxx.shtml')
    referer = 'http://www.cdgy.gov.cn/cdsjxw/c132946/zwxx.shtml'
    base_url = 'http://www.cdgy.gov.cn/cdsjxw/c132946/zwxx_{}.shtml'
    for i in range(2, page_count+1):
        url = base_url.format(i)
        parse_page(url, referer=referer)
        referer = url
        time.sleep(2)


def parse_page_count(url):
    source = get_html(url=url)
    if source is None:
        return
    page_count = re.findall(r'createPageHTML\(\'page_div\',(\d+),.*?\)|$', source)[0]
    if page_count == '':
        raise Exception('get page count failed')
    else:
        return int(page_count)


def run(url):
    global COL
    COL.ensure_index("url", unique=True)
    page_count = parse_page_count(url)
    time.sleep(2)
    parse_pages(page_count)


def main():
    setup_log(logging.INFO, os.path.join(os.path.abspath('.'), '../logs', 'cdsjxw.log'))
    url = 'http://www.cdgy.gov.cn/cdsjxw/c132946/zwxx.shtml'
    run(url)


if __name__ == '__main__':
    main()