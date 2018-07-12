# -*- coding: utf-8 -*-
import re
import time
import logging

import scrapy
from lxml import etree
from gov_info.items import GovInfoItem

from gov_info.settings import MONGODB_COLLECTION
from gov_info.common.utils import get_col


class CdibiSpider(scrapy.Spider):
    name = 'cdibi'
    download_delay = 5
    max_page = 5
    mongo_col = get_col(MONGODB_COLLECTION)
    mongo_col.ensure_index("unique_id", unique=True)
    start_urls = [
        'http://www.cdibi.org.cn/',
    ]
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,und;q=0.7',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Host': 'www.cdibi.org.cn',
        'Pragma': 'no-cache',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36',
    }

    custom_settings = {
        'LOG_FILE': f'logs/{name}.log',
        'ITEM_PIPELINES': {
            'gov_info.pipelines.GovInfoPipeline': 100,
        },
    }

    def parse(self, response):
        for sel in response.xpath(r'//div[@class="news"]/ul/li'):
            for page in range(1, self.max_page+1):
                url = sel.xpath('a/@href').extract_first(default='') + f'&page={page}&per-page=10'
                yield scrapy.FormRequest(url, method='GET', headers=self.headers, callback=self.parse_page)

    def parse_page(self, response):
        regex = '//ul[@class="news-list"]/li'
        for sel in response.xpath(regex):
            link = sel.xpath(r'a/@href').extract_first(default='').strip()
            title = sel.xpath(r'a/text()').extract_first(default='').strip()
            date = sel.xpath(r'span/text()').extract_first(default='').strip()
            lst = [link, title, date]
            if not all(lst):
                logging.warning(f'{response.url}--{link}: get data failed')
                continue
            url = link
            if self.mongo_col.find_one({'unique_id': title}):
                logging.warning(f'{title} is download already')
                continue
            date = date.strip('[').strip(']')
            if len(date) == 10:
                now = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
                date += ' ' + now.split(' ')[-1]
            item = GovInfoItem()
            item['url'] = url
            item['unique_id'] = title
            item['title'] = title
            item['source'] = '成都高新区创新创业服务中心'
            item['date'] = date
            item['origin'] = self.name
            item['type'] = 'web'
            item['location'] = '高新区'
            item['crawled'] = 1
            yield scrapy.FormRequest(url, method='GET', headers=self.headers,
                                     meta={'item': item}, callback=self.parse_item)

    def parse_item(self, response):
        selector = etree.HTML(response.body)
        item = response.meta['item']
        regex = r'//div[@class="news-detail"]'
        try:
            content = response.xpath(regex).xpath('string(.)').extract_first(default='').strip()
        except Exception as err:
            logging.error(f'{item["url"]}: get content failed')
        else:
            if content == '':
                logging.warning('content is none')
                return
            item['summary'] = content[:100]
            try:
                content = etree.tostring(selector.xpath(regex)[0], encoding='utf-8')
            except Exception as err:
                logging.error(f'{item["url"]}: get content failed')
                return
            item['content'] = content.decode('utf-8').replace('&#13;', '')
            yield item
