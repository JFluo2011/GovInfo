# -*- coding: utf-8 -*-
import re
import time
import datetime
import logging

import scrapy
from pymongo.errors import DuplicateKeyError
from gov_info.items import GovInfoItem

from gov_info.settings import WXINFOS, MONGODB_COLLECTION
from gov_info.common.utils import get_col, get_redis_client


class WxgzhSpider(scrapy.Spider):
    name = 'wxgzh'
    download_delay = 5
    task_col = get_col('wxgzh_task')
    mongo_col = get_col(MONGODB_COLLECTION)
    redis_client = get_redis_client()
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Host': 'mp.weixin.qq.com',
        'Pragma': 'no-cache',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.87 Safari/537.36',
    }

    custom_settings = {
        'ITEM_PIPELINES': {
            'gov_info.pipelines.WxgzhPipeline': 100,
        },
        'DOWNLOADER_MIDDLEWARES': {
            'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': 110,
            'gov_info.middlewares.WxgzhTaskRotateProxiesSpiderMiddleware': 100,
        },
    }

    def start_requests(self):
        self.mongo_col.update({'$and': [{'type': 'wxgzh'}, {'crawled': {'$ne': 1}}]},
                              {'$set': {'crawled': 0}}, multi=True)
        while True:
            task = self.mongo_col.find_one_and_update({'crawled': 0}, {'$set': {'crawled': 2}})
            if task is None:
                time.sleep(5)
                continue
            yield scrapy.FormRequest(task['url'], method='GET', headers=self.headers, meta={'task': task})

    def parse(self, response):
        item = GovInfoItem()
        task = response.meta['task']
        title = response.xpath(r'//*[@id="activity-name"]/text()').extract_first(default=None)
        if title is None:
            logging.error(f'{task["url"]}: get title failed')
            self.task_col.update({'unique_id': task['task_unique_id']}, {"$set": {'crawled': -1}})
            self.mongo_col.find_one_and_delete({'_id': task['_id']})
            return
        else:
            self.mongo_col.update({'_id': task['_id']}, {"$set": {'crawled': 1}})
        try:
            content = response.xpath(r'//*[@id="js_content"]')[0].xpath('string(.)').extract_first('')
        except Exception as err:
            logging.error(f'{task["url"]}: get content failed')
            self.task_col.update({'unique_id': task['task_unique_id']}, {"$set": {'crawled': -1}})
            self.mongo_col.find_one_and_delete({'_id': task['_id']})
            return
        item['title'] = title
        item['unique_id'] = task['unique_id']
        item['content'] = content
        yield item
