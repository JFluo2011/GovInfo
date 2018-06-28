import time
import re
import os
import copy
import logging

import requests
from lxml import etree

from common.utils import get_col, setup_log, get_proxy, get_redis_client, get_html
from local_config import MONGODB_COLLECTION


HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'Pragma': 'no-cache',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.87 Safari/537.36',
}
SESSION = requests.session()

# COL = get_col(MONGODB_COLLECTION)
COL = get_col('scst')
REDIS_CLIENT = get_redis_client()
COUNT = 0


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
    text = selector.xpath(r'//div[@class="msgbar"]')[0].xpath('string(.)')
    text = ''.join(text.replace('：', '').split())
    tmp, promulgator = re.findall(r'发布时间(.*?)来源(.*?)取消', text)[0]
    date = re.findall(r'(\d{4}-\d{2}-\d{2})', tmp)[0]
    time_ = re.findall(r'(\d{2}:\d{2}:\d{2})|$', tmp)[0]
    date += (' ' + time_) if time_ != '' else ''
    if '本站原创' in promulgator:
        promulgator = '四川省科学技术厅'
    item.update({'date': date, 'source': promulgator})
    try:
        content = selector.xpath(r'//div[@class="newsCon"]')[0].xpath('string(.)')
        item.update({'content': content})
    except Exception as err:
        logging.error(f'{url}: {err.__class__.__name__}: {str(err)}')
    finally:
        insert_item(item)


def parse_page(url):
    global COL
    global COUNT
    global HEADERS
    headers = copy.deepcopy(HEADERS)
    stop = False
    base_url = 'http://www.scst.gov.cn'
    source = get_html(url, headers=headers, byte_=True)
    if source is None:
        return False
    selector = etree.HTML(source)
    for sel in selector.xpath(r'//div[contains(@class, "news_right")]//h2'):
        link = base_url + sel.xpath(r'a/@href')[0]
        if COL.find_one({'url': link}):
            stop = True
            logging.warning(f'{link} is download already')
            continue
        item = {
            'url': link,
            'unique_id': link,
            'title': sel.xpath(r'a/@title')[0],
            'origin': 'scst',
            'summary': '',
            'type': 'web',
        }
        parse_info(item, link)
        COUNT += 1
        if COUNT % 100 == 0:
            print(f'count: {COUNT}')
        time.sleep(3)
    return stop


def parse_pages(page_count, type_):
    if type_ == 'tz':
        base_url = 'http://www.scst.gov.cn/tz/index_{}.jhtml'
    else:
        base_url = 'http://www.scst.gov.cn/gs/index_{}.jhtml'
    for i in range(1, page_count+1):
        url = base_url.format(i)
        parse_page(url)
        # if parse_page(url):
        #     break
        time.sleep(2)


def parse_page_count(url):
    global HEADERS
    headers = copy.deepcopy(HEADERS)
    text = get_html(url=url, headers=headers)
    page_count = re.findall(r'共\d+条记录\s*\d+/(\d+)\s*页|$', text)[0]
    if page_count == '':
        raise Exception('get page count failed')
    else:
        return int(page_count)


def run(url, type_):
    global COL
    COL.ensure_index("unique_id", unique=True)
    page_count = parse_page_count(url)
    time.sleep(2)
    parse_pages(page_count, type_)


def main():
    setup_log(logging.INFO, os.path.join(os.path.abspath('.'), '../logs', 'scst.log'))
    lst = [
        ('http://www.scst.gov.cn/tz/index.jhtml', 'tz'),
        ('http://www.scst.gov.cn/gs/index.jhtml', 'gs'),
    ]
    for url, type_ in lst:
        run(url, type_)


if __name__ == '__main__':
    main()
