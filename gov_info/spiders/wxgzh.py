# -*- coding: utf-8 -*-
import re
import time
import datetime
import logging

import scrapy
from lxml import etree
from pymongo.errors import DuplicateKeyError
from gov_info.items import GovInfoItem
from scrapy_redis.spiders import RedisSpider

from gov_info.settings import WXINFOS, MONGODB_COLLECTION
from gov_info.common.utils import get_col, get_redis_client


# class WxgzhSpider(scrapy.Spider):
class WxgzhSpider(RedisSpider):
    name = 'wxgzh'
    download_delay = 5
    handle_httpstatus_list = [403, 408, 564, 503]
    task_col = get_col('wxgzh_task')
    mongo_col = get_col(MONGODB_COLLECTION)
    redis_con = get_redis_client()
    redis_key = 'wxgzh'
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
        'DOWNLOAD_TIMEOUT': 60,
        'LOG_FILE': f'logs/{name}.log',
        'ITEM_PIPELINES': {
            'gov_info.pipelines.GovInfoPipeline': 100,
            # 'scrapy_redis.pipelines.RedisPipeline': 200,
        },
        'DOWNLOADER_MIDDLEWARES': {
            'gov_info.middlewares.RotateUserAgentMiddleware': 400,
            'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': 110,
            'gov_info.middlewares.WxgzhSpiderMiddleware': 100,
        },
    }

    # def start_requests(self):
    #     self.mongo_col.update({'$and': [{'type': 'wxgzh'}, {'crawled': {'$ne': 1}}]},
    #                           {'$set': {'crawled': 0}}, multi=True)
    #     while True:
    #         task = self.mongo_col.find_one_and_update({'crawled': 0}, {'$set': {'crawled': 2}})
    #         if task is None:
    #             time.sleep(5)
    #             continue
    #         yield scrapy.FormRequest(task['url'], method='GET', headers=self.headers, meta={'task': task})

    def parse(self, response):
        json_data = response.meta['json_data']
        item = GovInfoItem(json_data['item'])
        selector = etree.HTML(response.body)
        title = response.xpath(r'//*[@id="activity-name"]/text()').extract_first(default=None)
        if title is None:
            logging.error(f'{item["url"]}: get title failed')
            self.task_col.update({'unique_id': item['task_unique_id']}, {"$set": {'crawled': -1}})
            return

        regex = r'//*[@id="js_content"]'
        try:
            content = response.xpath(regex).xpath('string(.)').extract_first('')
        except Exception as err:
            logging.error(f'{item["url"]}: get content failed')
            self.task_col.update({'unique_id': item['task_unique_id']}, {"$set": {'crawled': -1}})
            return
        if content == '':
            logging.warning('content is none')
            return
        try:
            content = etree.tostring(selector.xpath(regex)[0], encoding='utf-8')
        except Exception as err:
            logging.error(f'{item["url"]}: get content failed')
            return
        item['summary'] = item['summary']
        if item['summary'] == '':
            item['summary'] = content.strip()[:100]
        item['content'] = content.decode('utf-8').replace('&#13;', '')
        item['title'] = title.strip()
        item['unique_id'] = item['unique_id']
        yield item
