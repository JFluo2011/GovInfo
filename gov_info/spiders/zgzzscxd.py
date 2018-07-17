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


class ZgzzscxdSpider(scrapy.Spider):
    name = 'zgzzscxd'
    download_delay = 5
    max_page = 5
    mongo_col = get_col(MONGODB_COLLECTION)
    mongo_col.create_index([("unique_id", pymongo.DESCENDING), ('origin', pymongo.DESCENDING)], unique=True)
    ntys = ['1', '3']
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Host': 'www.zgzzscxd.com',
        'Origin': 'http://www.zgzzscxd.com',
        'Pragma': 'no-cache',
        'Referer': 'http://www.zgzzscxd.com/NewsList.aspx?NTY=1',
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
        url = 'http://www.zgzzscxd.com/NewsList.aspx?NTY={}'
        for nty in self.ntys:
            yield scrapy.FormRequest(url.format(nty), method='GET', headers=self.headers)

    def parse(self, response):
        page_count = max([
            int(sel.xpath('text()').extract_first(default=''))
            for sel in response.xpath(r'//div[@id="AspNetPager1"]/a')
            if sel.xpath('text()').extract_first(default='').isdigit()
        ])
        page_count = min([page_count, self.max_page])
        for page in range(2, page_count+1):
            url = 'http://www.zgzzscxd.com/NewsList.aspx?NTY=1'
            form_data = {
                '__VIEWSTATE': response.xpath(r'//*[@id="__VIEWSTATE"]/@value').extract()[0],
                '__EVENTTARGET': 'AspNetPager1',
                '__EVENTARGUMENT': str(page),
                'AspNetPager1_input': '2',
            }
            yield scrapy.FormRequest(url, method='POST', headers=self.headers,
                                     formdata=form_data, callback=self.parse_page)
        for request in self.parse_page(response):
            yield request

    def parse_page(self, response):
        base_url = 'http://www.zgzzscxd.com/'
        for sel in response.xpath('//li[@class="clearfix"]'):
            item = GovInfoItem()
            link = sel.xpath('a/@href').extract_first(default='').strip()
            title = sel.xpath('a/@title').extract_first(default='').strip()
            lst = [link, title]
            if not all(lst):
                logging.warning(f'{response.url}: get data failed')
                continue
            url = base_url + link
            unique_id = get_md5(url)
            if self.mongo_col.find_one({'$and': [{'unique_id': unique_id}, {'origin': f'{self.name}'}]}):
                logging.warning(f'{url} is download already, unique_id: {unique_id}')
                continue

            item['url'] = url
            item['unique_id'] = unique_id
            item['title'] = title
            item['source'] = '成都市经济和信息化委员会'
            item['origin'] = self.name
            item['type'] = 'web'
            item['location'] = '成都市'
            item['crawled'] = 1
            yield scrapy.FormRequest(url, method='GET', headers=self.headers,
                                     meta={'item': item}, callback=self.parse_item)

    def parse_item(self, response):
        item = response.meta['item']
        selector = etree.HTML(response.body)
        regex = r'//div[@class="aa5"]'
        date = response.xpath(r'//div[@class="aa2"]/span[2]/text()').extract_first(default='').strip()
        content = response.xpath(regex).xpath('string(.)').extract_first(default='').strip()
        if date == '':
            logging.warning(f'{item["url"]}: date is none')
            return
        date = date.replace('：', ':').split(':', 1)[-1].replace('/', '-')
        date = time.strftime("%Y-%m-%d %H:%M:%S", time.strptime(date, "%Y-%m-%d %H:%M:%S"))
        item['summary'] = content[:100] if (content != '') else item['title']
        try:
            content = etree.tostring(selector.xpath(regex)[0], encoding='utf-8')
        except Exception as err:
            logging.error(f'{item["url"]}: get content failed')
            return
        item['content'] = content.decode('utf-8').replace('&#13;', '')
        item['date'] = date
        yield item
