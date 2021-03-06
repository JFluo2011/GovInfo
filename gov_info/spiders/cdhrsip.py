# -*- coding: utf-8 -*-
import re
import time
import copy
import json
import logging

import pymongo
import scrapy
from lxml import etree
from gov_info.items import GovInfoItem

from gov_info.settings import MONGODB_COLLECTION
from gov_info.common.utils import get_col, get_md5


class CdhrsipSpider(scrapy.Spider):
    name = 'cdhrsip'
    download_delay = 5
    max_page = 5
    mongo_col = get_col(MONGODB_COLLECTION)
    mongo_col.create_index([("unique_id", pymongo.DESCENDING), ('origin', pymongo.DESCENDING)], unique=True)
    type_lst = ['001', '101']
    headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,und;q=0.7',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Content-Length': '0',
        'Host': 'www.cdhrsip.com',
        'Origin': 'http://www.cdhrsip.com',
        'Pragma': 'no-cache',
        'Referer': 'http://www.cdhrsip.com/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest',
    }
    base_params = {
        'notifi': '1',
        'pageNo': '5',
        'pageSize': '10',
        'orderPublish': '1'
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
        base_url = 'http://www.cdhrsip.com/article/newsInfo?id={}'
        json_data = json.loads(response.body)
        records = json_data['records']
        for record in records:
            url = base_url.format(record['id'])
            unique_id = get_md5(str(record['id']))
            if self.mongo_col.find_one({'$and': [{'unique_id': unique_id}, {'origin': f'{self.name}'}]}):
                logging.warning(f'{url} is download already, unique_id: {unique_id}')
                continue
            selector = etree.HTML(record['content'])
            summary = selector.xpath('string(.)').strip()[:100]
            summary = summary if (summary not in [b'', '']) else record['title']

            date = record['publishTime']
            if len(date) == 10:
                now = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
                date += ' ' + now.split(' ')[-1]
            item = GovInfoItem()
            item['url'] = url
            item['unique_id'] = unique_id
            item['title'] = record['title']
            item['summary'] = summary
            item['source'] = record['author']
            item['date'] = date
            item['origin'] = self.name
            item['type'] = 'web'
            item['location'] = '成都市'
            item['crawled'] = 1
            item['content'] = record['content']
            yield item

    def create_request(self, type_):
        params = copy.deepcopy(self.base_params)
        params.update({'type': type_})
        url = 'http://www.cdhrsip.com/article/list'
        for page in range(1, self.max_page + 1):
            params.update({'pageNo': str(page)})
            yield scrapy.FormRequest(url, method='GET', formdata=params, headers=self.headers)
