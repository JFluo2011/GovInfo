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
    'Host': 'www.cdht.gov.cn',
    'Pragma': 'no-cache',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.87 Safari/537.36',
}
SESSION = requests.session()

COL = get_col(MONGODB_COLLECTION)
REDIS_CLIENT = get_redis_client()


def get_html(url, referer='', byte_=False):
    global HEADERS
    headers = copy.deepcopy(HEADERS)
    if referer != '':
        headers.update({'Referer': referer})
    # proxies = {'http': get_proxy(REDIS_CLIENT)}
    proxies = None
    try:
        r = requests.get(url, headers=headers, proxies=proxies)
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
    source = get_html(url)
    if source is None:
        return
    selector = etree.HTML(source)
    try:
        content = selector.xpath(r'//div[@id="d_content"]')[0].xpath('string(.)')
        item.update({'content': content})
    except Exception as err:
        logging.error(f'{url}: {err.__class__.__name__}: {str(err)}')
    finally:
        insert_item(item)


def parse_page(url):
    global COL
    count = 0
    stop = False
    source = get_html(url)
    if source is None:
        return False
    selector = etree.HTML(source)
    regex = '//div[@class="news-list-list"]/table[@class="table"]/tbody/tr'
    for sel in selector.xpath(regex):
        link = sel.xpath(r'td[1]/a/@href')[0]
        if COL.find_one({'url': link}):
            stop = True
            logging.warning(f'{link} is download already')
            continue
        try:
            item = {
                'url': link,
                'title': sel.xpath(r'td[1]/a/text()')[0],
                'promulgator': sel.xpath(r'td[2]/text()')[0],
                'date': sel.xpath(r'td[3]/span/text()')[0],
                'origin': 'cdht',
            }
        except Exception as err:
            logging.error(f'{url}: {err.__class__.__name__}: {str(err)}')
            continue
        parse_info(item, link)
        if count % 100:
            print(f'count: {count}')
        time.sleep(2)
    return stop


def parse_pages(page_count):
    base_url = 'http://www.cdht.gov.cn/zwgktzgg/index_{}.jhtml'
    for i in range(1, page_count+1):
        url = base_url.format(i)
        if parse_page(url):
            break
        time.sleep(2)


def parse_page_count(url):
    source = get_html(url=url)
    page_count = re.findall(r'共\d+条记录\s*\d+/(\d+)\s*页|$', source)[0]
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
    setup_log(logging.INFO, os.path.join(os.path.abspath('.'), '../logs', 'cdht.log'))
    url = 'http://www.cdht.gov.cn/zwgktzgg/index.jhtml'
    run(url)


if __name__ == '__main__':
    main()
