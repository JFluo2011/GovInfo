# -*- coding: utf-8 -*-
import re
import time
import datetime
import logging
import copy
import json

import scrapy
from pymongo.errors import DuplicateKeyError
from gov_info.items import GovInfoItem

from gov_info.settings import WXINFOS, MONGODB_COLLECTION
from gov_info.common.utils import get_col, get_redis_client


class WxgzhTaskSpider(scrapy.Spider):
    name = 'wxgzh_task'
    download_delay = 5
    days = 5
    task_col = get_col('wxgzh_task')
    task_col.ensure_index("unique_id", unique=True)
    mongo_col = get_col(MONGODB_COLLECTION)
    mongo_col.ensure_index("unique_id", unique=True)
    redis_con = get_redis_client()
    redis_key = 'wxgzh'
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Host': 'weixin.sogou.com',
        'Pragma': 'no-cache',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.87 Safari/537.36',
    }

    custom_settings = {
        'LOG_FILE': f'logs/{name}.log',
        'ITEM_PIPELINES': {
            'gov_info.pipelines.WxgzhTaskPipeline': 100,
        },
        'DOWNLOADER_MIDDLEWARES': {
            'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': 110,
            'gov_info.middlewares.WxgzhTaskRotateProxiesSpiderMiddleware': 100,
        },
        # # redis
        # 'SCHEDULER': "scrapy_redis.scheduler.Scheduler",
        # 'DUPEFILTER_CLASS': "gov_info.common.utils.MyRFPDupeFilter",
        # 'SCHEDULER_PERSIST': True,
        # 'REDIS_START_URLS_AS_SET': True
    }

    def start_requests(self):
        url = 'http://weixin.sogou.com/weixin'
        self.task_col.update({'crawled': {'$ne': 1}}, {'$set': {'crawled': 0}}, multi=True)
        for wx_info in WXINFOS:
            self.create_task(wx_info)
        while True:
            task = self.task_col.find_one_and_update({'crawled': 0}, {'$set': {'crawled': 2}})
            if task is None:
                break
            params = task['params']
            self.headers.update({'Referer': task['referer']})
            yield scrapy.FormRequest(url, method='GET', formdata=params, headers=self.headers, meta={'task': task})

    def parse(self, response):
        result = 1
        url = response.url
        task = response.meta['task']
        params = task['params']
        origin = task['origin']
        total = re.findall(r'找到约(\d+)条结果|$'.encode('utf-8'), response.body)[0]
        if total != b'' and int(total) > 10:
            result = -1
            logging.error(f'{url}: {params} page too more')
        self.task_col.update({'_id': task['_id']}, {"$set": {'crawled': result}})

        redis_values = []
        for sel in response.xpath(r'//li[contains(@id, "sogou_vr_")]'):
            item = GovInfoItem()
            unique_id = sel.xpath(r'./@d').extract_first(default='').strip()
            date = sel.xpath(r'div/div/@t').extract_first(default='').strip()
            source = sel.xpath(r'div/div/a/text()').extract_first(default='').strip()
            link = sel.xpath(r'div/h3/a/@href').extract_first(default='').strip()
            name = sel.xpath(r'div/div/a/text()').extract_first(default='').strip()
            lst = [unique_id, date, source, link]
            if not all(lst):
                result = -1
                logging.warning(f'{url}: {params}.{link}: get data failed')
                self.task_col.update({'_id': task['_id']}, {"$set": {'crawled': result}})
                continue
            if self.mongo_col.find_one({'unique_id': unique_id}):
                logging.warning(f'{link} is already downloaded')
                continue
            if task['name'] != name:
                logging.warning(f'{url}: {params}.{link}: is not publish from {task["name"]}')
                continue
            link = link.replace('http', 'https')
            item['url'] = link
            item['task_unique_id'] = task['unique_id']
            item['unique_id'] = unique_id
            try:
                item['summary'] = sel.xpath(r'./div/p[@class="txt-info"]')[0].xpath('string(.)').extract_first('')
            except Exception as err:
                logging.warning(f'{url}: {params}.{link}: get summary failed')
                item['summary'] = ''
            item['date'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(date)))
            item['source'] = source
            item['origin'] = origin
            item['type'] = 'wxgzh'
            item['crawled'] = 0
            item['location'] = task['location']
            redis_values.append(json.dumps({'item': dict(item)}))
        if redis_values:
            self.redis_con.sadd("{}".format(self.redis_key), *redis_values)

    def create_task(self, wx_info):
        url = 'http://weixin.sogou.com/weixin'
        params = {
            'type': '2',
            'ie': 'utf8',
            'query': wx_info.name,
            'tsn': '5',
            'interation': '',
            'wxid': wx_info.wx_id,
            'usip': wx_info.name,
        }
        date = datetime.datetime.now()
        days = self.days
        while days >= 0:
            t = date.strftime("%Y-%m-%d")
            data = {
                'url': url,
                'name': wx_info.name,
                'unique_id': f'{wx_info.origin}-{t}',
                'origin': wx_info.origin,
                'params': params,
                'referer': wx_info.referer,
                'crawled': 0,
                'location': wx_info.location,
            }
            date -= datetime.timedelta(days=1)
            days -= 1
            params.update({'ft': t, 'et': t})
            try:
                self.task_col.insert(data)
            except DuplicateKeyError:
                # logging.warning(f'task unique_id {wx_info.origin}-{t} already exists')
                pass
