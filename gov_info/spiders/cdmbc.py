# -*- coding: utf-8 -*-
import re
import time
import copy
import json
import logging

import pymongo
import xmltodict
import scrapy
from lxml import etree
from gov_info.items import GovInfoItem

from gov_info.settings import MONGODB_COLLECTION
from gov_info.common.utils import get_col, get_md5


class CdmbcSpider(scrapy.Spider):
    name = 'cdmbc'
    download_delay = 5
    max_page = 5
    mongo_col = get_col(MONGODB_COLLECTION)
    mongo_col.create_index([("unique_id", pymongo.DESCENDING), ('origin', pymongo.DESCENDING)], unique=True)
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
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
        headers = copy.deepcopy(self.headers)
        headers.update({
            'X-Requested-With': 'XMLHttpRequest',
            'Host': 'swgl.cdmbc.gov.cn'
        })
        url = 'http://swgl.cdmbc.gov.cn/egrantweb/notice/noticeList?flag=grid&noticeType=3'
        yield scrapy.FormRequest(url, method='GET', headers=headers)

    def parse(self, response):
        json_data = json.loads(json.dumps(xmltodict.parse(response.body)))
        page_count = json_data['rows'].get('total', None)
        if page_count is None:
            logging.error('get page_count failed')
            return
        form_data = {
            '_search': 'false',
            'nd': str(int(time.time()*1000)),
            'rows': '10',
            'sidx': '',
            'sord': 'desc',
            'searchString': '',
        }
        headers = copy.deepcopy(self.headers)
        headers.update({
            'X-Requested-With': 'XMLHttpRequest',
            'Host': 'swgl.cdmbc.gov.cn'
        })
        page_count = min(int(page_count), self.max_page)
        url = 'http://swgl.cdmbc.gov.cn/egrantweb/notice/noticeList?flag=grid&noticeType=3'
        for page in range(1, page_count+1):
            form_data.update({'page': str(page)})
            yield scrapy.FormRequest(url, method='POST', headers=headers,
                                     formdata=form_data, callback=self.parse_page)

    def parse_page(self, response):
        headers = copy.deepcopy(self.headers)
        headers.update({'Host': 'www.cdmbc.gov.cn'})
        json_data = json.loads(json.dumps(xmltodict.parse(response.body)))
        for row in json_data['rows']['row']:
            url = re.findall(r'href="(.*?)"|$', row['cell'][0])[0]
            if url == '' or 'cdmbc' not in url:
                logging.warning(f'{response.url}--{url}: get data failed')
                continue
            date = row['cell'][1]
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
            item['source'] = '成都市商务委'
            item['date'] = date
            item['origin'] = self.name
            item['type'] = 'web'
            item['location'] = '成都市'
            item['crawled'] = 1
            yield scrapy.FormRequest(url, method='GET', headers=headers,
                                     meta={'item': item}, callback=self.parse_item)

    def parse_item(self, response):
        item = response.meta['item']
        selector = etree.HTML(response.body)
        regex = r'//div[@id="detail"]'
        title = response.xpath(r'//div[@class="detailBox"]/h2/text()').extract_first(default='').strip()
        content = response.xpath(regex).xpath('string(.)').extract_first(default='').strip()
        if (title == '') and (content == ''):
            logging.warning(f'{item["url"]}: title and content is none')
            return
        item['summary'] = content[:100] if (content != '') else title
        try:
            content = etree.tostring(selector.xpath(regex)[0], encoding='utf-8')
        except Exception as err:
            logging.error(f'{item["url"]}: get content failed')
            return
        item['content'] = content.decode('utf-8').replace('&#13;', '')
        item['title'] = title
        yield item
