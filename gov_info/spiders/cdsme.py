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


class CdsmeSpider(scrapy.Spider):
    name = 'cdsme'
    download_delay = 5
    max_page = 5
    mongo_col = get_col(MONGODB_COLLECTION)
    mongo_col.create_index([("unique_id", pymongo.DESCENDING), ('origin', pymongo.DESCENDING)], unique=True)
    start_urls = [
        'http://www.cdsme.com/list.aspx?id=79&Model_id=9&page={}',
        'http://www.cdsme.com/search.aspx?m=zhengcexinxi&page={}',
    ]
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,und;q=0.7',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Host': 'www.cdsme.com',
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

    def start_requests(self):
        for url in self.start_urls:
            for page in range(1, self.max_page + 1):
                yield scrapy.FormRequest(url.format(page), method='GET', headers=self.headers)

    def parse(self, response):
        base_url = 'http://www.cdsme.com'
        regex = '//div[@class="clearFix MN_A1_box"]'
        for sel in response.xpath(regex):
            link = sel.xpath(r'div[1]/a/@href').extract_first(default='').strip()
            summary = sel.xpath(r'div[2]/div/p/text()').extract_first(default='').strip()
            date = sel.xpath(r'div[1]/p/text()').extract_first(default='').strip()
            lst = [link, date]
            if not all(lst):
                logging.warning(f'{response.url}--{link}: get data failed')
                continue
            url = base_url + link
            unique_id = get_md5(url)
            if self.mongo_col.find_one({'$and': [{'unique_id': unique_id}, {'origin': f'{self.name}'}]}):
                logging.warning(f'{url} is download already, unique_id: {unique_id}')
                continue
            date = date.strip('[').strip(']')
            if len(date) == 10:
                now = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
                date += ' ' + now.split(' ')[-1]
            item = GovInfoItem()
            item['url'] = url
            item['unique_id'] = unique_id
            item['summary'] = summary
            item['source'] = '成都市中小企业网'
            item['date'] = date
            item['origin'] = self.name
            item['type'] = 'web'
            item['location'] = '成都市'
            item['crawled'] = 1
            yield scrapy.FormRequest(url, method='GET', headers=self.headers,
                                     meta={'item': item}, callback=self.parse_item)

    def parse_item(self, response):
        selector = etree.HTML(response.body)
        item = response.meta['item']
        regex = r'//div[@id="neirong"]'
        title = response.xpath(r'//div[@class="JR_A1_box"]/p/text()').extract_first(default='').strip()
        content = response.xpath(regex).xpath('string(.)').extract_first(default='').strip()
        if title == '' and content == '':
            logging.warning(f'{item["url"]}: title and content is none')
            return
        if item['summary'] == '':
            item['summary'] = content[:100] if (content != '') else item['title']
        try:
            content = etree.tostring(selector.xpath(regex)[0], encoding='utf-8')
        except Exception as err:
            logging.error(f'{item["url"]}: get content failed')
            return
        item['content'] = content.decode('utf-8').replace('&#13;', '')
        item['title'] = title
        yield item
