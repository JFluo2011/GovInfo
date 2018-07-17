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


class ScstSpider(scrapy.Spider):
    name = 'scst'
    download_delay = 5
    max_page = 5
    mongo_col = get_col(MONGODB_COLLECTION)
    mongo_col.create_index([("unique_id", pymongo.DESCENDING), ('origin', pymongo.DESCENDING)], unique=True)
    start_urls = [
        'http://www.scst.gov.cn/tz/index.jhtml',
        'http://www.scst.gov.cn/gs/index.jhtml',
    ]
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Pragma': 'no-cache',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.87 Safari/537.36',
    }

    custom_settings = {
        'LOG_FILE': f'logs/{name}.log',
        'ITEM_PIPELINES': {
            'gov_info.pipelines.GovInfoPipeline': 100,
        },
    }

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.FormRequest(url, method='GET', headers=self.headers)

    def parse(self, response):
        page_count = re.findall(r'共\d+条记录\s*\d+/(\d+)\s*页|$'.encode('utf-8'), response.body)[0]
        if page_count == b'':
            raise Exception('get page count failed')

        page_count = min(int(page_count), self.max_page)
        if 'tz' in response.url:
            base_url = 'http://www.scst.gov.cn/tz/index_{}.jhtml'
        else:
            base_url = 'http://www.scst.gov.cn/gs/index_{}.jhtml'
        for i in range(1, int(page_count) + 1):
            url = base_url.format(i)
            yield scrapy.FormRequest(url, method='GET', headers=self.headers, callback=self.parse_page)

    def parse_page(self, response):
        base_url = 'http://www.scst.gov.cn'
        regex = r'//div[contains(@class, "news_right")]//h2'
        for sel in response.xpath(regex):
            link = sel.xpath(r'a/@href').extract_first(default='').strip()
            title = sel.xpath(r'a/@title').extract_first(default='').strip()
            lst = [link, title]
            if not all(lst):
                logging.warning(f'{response.url}.{link}: get data failed')
                continue
            url = base_url + link
            unique_id = get_md5(url)
            if self.mongo_col.find_one({'$and': [{'unique_id': unique_id}, {'origin': f'{self.name}'}]}):
                logging.warning(f'{url} is download already, unique_id: {unique_id}')
                continue
            item = GovInfoItem()
            item['url'] = url
            item['unique_id'] = unique_id
            item['title'] = title.strip()
            item['origin'] = self.name
            item['type'] = 'web'
            item['location'] = '四川省'
            item['crawled'] = 1
            yield scrapy.FormRequest(url, method='GET', headers=self.headers,
                                     meta={'item': item}, callback=self.parse_item)

    def parse_item(self, response):
        item = response.meta['item']
        try:
            text = response.xpath(r'//div[@class="msgbar"]')[0].xpath('string(.)').extract_first(default='')
        except Exception as err:
            logging.error(f'{item["url"]}: get source and date failed')
            return
        text = ''.join(text.replace('：', '').split())
        tmp, source = re.findall(r'发布时间(.*?)来源(.*?)取消', text)[0]
        date = re.findall(r'(\d{4}-\d{2}-\d{2})', tmp)[0]
        time_ = re.findall(r'(\d{2}:\d{2}:\d{2})|$', tmp)[0]
        if time_ == '':
            time_ = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        date += (' ' + time_) if time_ != '' else ''
        if '本站原创' in source:
            source = '四川省科学技术厅'
        item['source'] = source
        item['date'] = date
        selector = etree.HTML(response.body)
        regex = r'//div[@class="newsCon"]'
        content = response.xpath(regex)[0].xpath('string(.)').extract_first(default='').strip()
        # if content == '':
        #     logging.warning(f'{item["url"]}: content is none')
        #     return
        item['summary'] = content[:100] if (content != '') else item['title']
        content = etree.tostring(selector.xpath(regex)[0], encoding='utf-8')
        item['content'] = content.decode('utf-8').replace('&#13;', '')
        yield item
