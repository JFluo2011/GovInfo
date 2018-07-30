# -*- coding: utf-8 -*-
import re
import time
import logging

import pymongo
import scrapy
from lxml import etree
from gov_info.items import GovInfoItem

from gov_info.settings import MONGODB_COLLECTION
from gov_info.common.utils import get_col, get_md5


class SczwfwSpider(scrapy.Spider):
    name = 'sczwfw'
    download_delay = 5
    max_page = 5
    mongo_col = get_col(MONGODB_COLLECTION)
    mongo_col.create_index([("unique_id", pymongo.DESCENDING), ('origin', pymongo.DESCENDING)], unique=True)
    start_urls = [
        'http://www.sczwfw.gov.cn:82/10000/10006/10008/index.shtml',
        'http://www.sczwfw.gov.cn:82/10000/10006/10002/index.shtml',
        'http://www.sczwfw.gov.cn:82/10000/10010/index.shtml',
        'http://www.sczwfw.gov.cn:82/10000/10003/index.shtml',
    ]
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Host': 'www.sczwfw.gov.cn:82',
        'Pragma': 'no-cache',
        'Referer': 'http://www.sczwfw.gov.cn/policylist.aspx?news=tzgg',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36',
    }

    custom_settings = {
        'LOG_FILE': f'logs/{name}.log',
        'ITEM_PIPELINES': {
            'gov_info.pipelines.GovInfoPipeline': 100,
        },
    }

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.FormRequest(url, method='GET', headers=self.headers, meta={'base_url': url})

    def parse(self, response):
        page_count = response.xpath(r'//input[@id="hPageCount"]/@value').extract_first(default='').strip()
        if page_count in [b'', '']:
            raise Exception('get page count failed')
        base_url = response.meta['base_url']
        page_count = min([int(page_count), self.max_page])
        for page in range(1, page_count):
            url = base_url.replace('index', 'index_{}').format(page)
            yield scrapy.FormRequest(url, method='GET', headers=self.headers, callback=self.parse_page)
        for request in self.parse_page(response):
            yield request

    def parse_page(self, response):
        base_url = 'http://www.sczwfw.gov.cn:82'
        for sel in response.xpath('//div[@class="news_r"]//li'):
            item = GovInfoItem()
            link = sel.xpath('.//a/@href').extract_first(default='').strip()
            title = sel.xpath('.//a/@title').extract_first(default='').strip()
            date = sel.xpath('.//em/text()').extract_first(default='').strip()
            lst = [link, title, date]
            if not all(lst):
                logging.warning(f'{response.url}: get data failed')
                continue
            url = base_url + link
            unique_id = get_md5(url)
            if self.mongo_col.find_one({'$and': [{'unique_id': unique_id}, {'origin': f'{self.name}'}]}):
                logging.warning(f'{url} is download already, unique_id: {unique_id}')
                continue

            if len(date) == 10:
                now = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
                date += ' ' + now.split(' ')[-1]

            item['url'] = url
            item['unique_id'] = unique_id
            item['title'] = title
            item['source'] = '四川省人民政府办公厅'
            item['origin'] = self.name
            item['date'] = date
            item['type'] = 'web'
            item['location'] = '四川省'
            item['crawled'] = 1
            yield scrapy.FormRequest(url, method='GET', headers=self.headers,
                                     meta={'item': item}, callback=self.parse_item)

    def parse_item(self, response):
        item = response.meta['item']
        selector = etree.HTML(response.body)
        regex = r'//div[@class="deta_ct"]'
        content = response.xpath(regex).xpath('string(.)').extract_first(default='').strip()
        # if content == '':
        #     logging.warning(f'{item["url"]}: date or content is none')
        #     return
        summary = content[:100] if (content != '') else item['title']
        try:
            content = etree.tostring(selector.xpath(regex)[0], encoding='utf-8')
        except Exception as err:
            logging.error(f'{item["url"]}: get content failed')
            return
        item['summary'] = summary.replace('&#13;', '').replace('em{font-style:normal;}', '')
        item['content'] = content.decode('utf-8').replace('&#13;', '').replace('em{font-style:normal;}', '')
        yield item
