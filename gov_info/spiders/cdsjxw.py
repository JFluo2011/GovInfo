# -*- coding: utf-8 -*-
import re
import copy
import logging

import scrapy
from gov_info.items import GovInfoItem

from gov_info.settings import MONGODB_COLLECTION
from gov_info.common.utils import get_col


class CdsjxwSpider(scrapy.Spider):
    name = 'cdsjxw'
    download_delay = 5
    mongo_col = get_col(MONGODB_COLLECTION)
    mongo_col.ensure_index("unique_id", unique=True)
    base_url = 'http://www.cdgy.gov.cn'
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Host': 'www.cdgy.gov.cn',
        'Pragma': 'no-cache',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.87 Safari/537.36',
    }

    custom_settings = {
        'ITEM_PIPELINES': {
            'gov_info.pipelines.GovInfoPipeline': 100,
        },
        'COOKIES_ENABLED': True
    }

    def start_requests(self):
        url = 'http://www.cdgy.gov.cn/cdsjxw/c132946/zwxx.shtml'
        yield scrapy.FormRequest(url, method='GET', headers=self.headers)

    def parse(self, response):
        page_count = re.findall(r'createPageHTML\(\'page_div\',(\d+),.*?\)|$'.encode('utf-8'), response.body)[0]
        if page_count == b'':
            raise Exception('get page count failed')

        referer = response.url
        base_url = 'http://www.cdgy.gov.cn/cdsjxw/c132946/zwxx_{}.shtml'
        for i in range(2, int(page_count) + 1):
            headers = copy.deepcopy(self.headers)
            headers.update({'referer': referer})
            url = base_url.format(i)
            referer = url
            yield scrapy.FormRequest(url, method='GET', headers=self.headers, callback=self.parse_page)

        for request in self.parse_page(response):
            yield request

    def parse_page(self, response):
        regex = '//div[@class="newlist_left_cont"]/ul'
        for sel in response.xpath(regex):
            link = sel.xpath(r'li[1]/a/@href').extract_first(default=None)
            text = sel.xpath(r'li[2]/text()').extract_first(default=None)
            title = sel.xpath(r'li[1]/a/@title').extract_first(default=None)
            lst = [link, title, text]
            if not any(lst):
                logging.warning(f'{response.url}.{link}: get data failed')
                continue
            link = self.base_url + link
            if self.mongo_col.find_one({'url': link}):
                logging.warning(f'{link} is download already')
                continue
            text = ''.join(text.split())
            text = re.sub(r'\s|:|：', '', text)
            promulgator, date = re.findall(r'来源(.*?)发布时间(\d{4}-\d{2}-\d{2})', text)[0]
            item = GovInfoItem()
            item['url'] = link
            item['unique_id'] = link
            item['title'] = title
            item['summary'] = ''
            item['source'] = date.strip('[').strip(']')
            item['date'] = date
            item['origin'] = 'cdsjxw'
            item['type'] = 'web'
            item['tag'] = '市'
            item['location'] = '成都市'
            item['crawled'] = 1
            yield scrapy.FormRequest(link, method='GET', headers=self.headers,
                                     meta={'item': item}, callback=self.parse_item)

    def parse_item(self, response):
        item = response.meta['item']
        try:
            content = response.xpath(r'//div[@id="top"]')[0].xpath('string(.)').extract_first(default='')
        except Exception as err:
            try:
                content = response.xpath(r'//div[@class="main-contshow"]')[0].xpath('string(.)').extract_first(default='')
            except Exception as err:
                logging.error(f'{item["url"]}: get content failed')
                return
        item['content'] = content
        yield item
