# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class GovInfoItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    url = scrapy.Field()
    task_unique_id = scrapy.Field()
    unique_id = scrapy.Field()
    summary = scrapy.Field()
    date = scrapy.Field()
    source = scrapy.Field()
    origin = scrapy.Field()
    type = scrapy.Field()
    content = scrapy.Field()
    title = scrapy.Field()
    tag = scrapy.Field()
    location = scrapy.Field()
    crawled = scrapy.Field()
    result = scrapy.Field()



