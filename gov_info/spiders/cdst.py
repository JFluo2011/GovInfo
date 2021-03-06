# -*- coding: utf-8 -*-
import time
import logging

import pymongo
import scrapy
from lxml import etree
from gov_info.items import GovInfoItem

from gov_info.settings import MONGODB_COLLECTION
from gov_info.common.utils import get_col, get_md5


class CdstSpider(scrapy.Spider):
    name = 'cdst'
    download_delay = 5
    max_page = 5
    mongo_col = get_col(MONGODB_COLLECTION)
    mongo_col.create_index([("unique_id", pymongo.DESCENDING), ('origin', pymongo.DESCENDING)], unique=True)
    type_lst = [
        ('22', '41'),
        ('22', '190'),
    ]
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Host': 'www.cdst.gov.cn',
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
        for type_ in self.type_lst:
            for request in self.create_request(type_):
                yield request

    def parse(self, response):
        base_url = 'http://www.cdst.gov.cn/Readnews.asp?NewsID={}'
        for sel in response.xpath(r'//div[@class="listline"]/li'):
            title = sel.xpath(r'a/@title').extract_first(default='').strip()
            unique_id = sel.xpath('a/@href').extract_first(default='').strip()
            date = sel.xpath(r'span/text()').extract_first(default='').strip()
            lst = [title, unique_id, date]
            if not all(lst):
                logging.warning(f'{response.url}: get data failed')
                continue
            url = base_url.format(unique_id.split('=')[-1])
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
            item['title'] = title
            item['source'] = '成都市科学技术局'
            item['date'] = date
            item['origin'] = self.name
            item['type'] = 'web'
            item['location'] = '成都市'
            item['crawled'] = 1
            yield scrapy.FormRequest(url, method='GET', headers=self.headers,
                                     meta={'item': item}, callback=self.parse_item)

    def parse_item(self, response):
        item = response.meta['item']
        selector = etree.HTML(response.body)
        regex = r'//div[@class="news_content"]'
        content = response.xpath(regex).xpath('string(.)').extract_first(default='').strip()
        # if content == '':
        #     logging.warning(f'{item["url"]}: content is none')
        #     return
        item['summary'] = content[:100] if (content != '') else item['title']
        try:
            content = etree.tostring(selector.xpath(regex)[0], encoding='utf-8')
        except Exception as err:
            logging.error(f'{item["url"]}: get content failed')
            return
        item['content'] = content.decode('utf-8').replace('&#13;', '')
        yield item

    def create_request(self, type_):
        params = {
            'TypeID': type_[0],
            'BigClassID': type_[1],
        }
        url = 'http://www.cdst.gov.cn/Type.asp'
        for page in range(1, self.max_page + 1):
            params.update({'page': str(page)})
            yield scrapy.FormRequest(url, method='GET', formdata=params, headers=self.headers)
