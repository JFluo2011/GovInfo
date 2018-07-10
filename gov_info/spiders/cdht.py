# -*- coding: utf-8 -*-
import re
import time
import logging

import scrapy
from lxml import etree
from gov_info.items import GovInfoItem

from gov_info.settings import MONGODB_COLLECTION
from gov_info.common.utils import get_col


class CdhtSpider(scrapy.Spider):
    name = 'cdht'
    download_delay = 5
    # mongo_col = get_col('cdht')
    mongo_col = get_col(MONGODB_COLLECTION)
    mongo_col.ensure_index("unique_id", unique=True)
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Host': 'www.cdht.gov.cn',
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
        url = 'http://www.cdht.gov.cn/zwgktzgg/index.jhtml'
        yield scrapy.FormRequest(url, method='GET', headers=self.headers)

    def parse(self, response):
        page_count = re.findall(r'共\d+条记录\s*\d+/(\d+)\s*页|$'.encode('utf-8'), response.body)[0]
        if page_count == b'':
            raise Exception('get page count failed')

        base_url = 'http://www.cdht.gov.cn/zwgktzgg/index_{}.jhtml'
        page_count = page_count if int(page_count) < 5 else 5
        for i in range(1, int(page_count) + 1):
            url = base_url.format(i)
            yield scrapy.FormRequest(url, method='GET', headers=self.headers, callback=self.parse_page)

    def parse_page(self, response):
        regex = '//div[@class="news-list-list"]/table[@class="table"]/tbody/tr'
        for sel in response.xpath(regex):
            link = sel.xpath(r'td[1]/a/@href').extract_first(default=None)
            title = sel.xpath(r'td[1]/a/text()').extract_first(default=None)
            source = sel.xpath(r'td[2]/text()').extract_first(default=None)
            date = sel.xpath(r'td[3]/span/text()').extract_first(default=None)
            lst = [link, title, source, date]
            if not any(lst):
                logging.warning(f'{response.url}.{link}: get data failed')
                continue
            if self.mongo_col.find_one({'url': link}):
                logging.warning(f'{link} is download already')
                continue
            date = date.strip('[').strip(']')
            if len(date) == 10:
                now = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
                date += ' ' + now.split(' ')[-1]
            item = GovInfoItem()
            item['url'] = link
            item['unique_id'] = link
            item['summary'] = ''
            item['source'] = source
            item['date'] = date
            item['origin'] = self.name
            item['type'] = 'web'
            item['tag'] = '区'
            item['location'] = '成都市高新区'
            item['crawled'] = 1
            yield scrapy.FormRequest(link, method='GET', headers=self.headers,
                                     meta={'item': item}, callback=self.parse_item)

    def parse_item(self, response):
        selector = etree.HTML(response.body)
        item = response.meta['item']
        regex = r'//div[@id="d_content"]'
        try:
            title = response.xpath(r'//div[@class="page"]/h1/text()').extract_first(default='').strip()
            content = response.xpath(regex).xpath('string(.)').extract_first(default='')
        except Exception as err:
            logging.error(f'{item["url"]}: get content failed')
        else:
            if title == '' or content == '':
                logging.warning('title or content is none')
                return
            if item['summary'] == '':
                item['summary'] = content.strip()[:100]
            try:
                content = etree.tostring(selector.xpath(regex)[0], encoding='utf-8')
            except Exception as err:
                logging.error(f'{item["url"]}: get content failed')
                return
            item['content'] = content.decode('utf-8').replace('&#13;', '')
            item['title'] = title
            yield item
