# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html
import logging
from scrapy.exceptions import DropItem


class GovInfoPipeline(object):
    def process_item(self, item, spider):
        data = {
            'url': item['url'],
            'unique_id': item['unique_id'],
            'summary': item['summary'],
            'date': item['date'],
            'source': item['source'],
            'origin': item['origin'],
            'type': item['type'],
            'location': item['location'],
            'title': item['title'],
            'content': item['content'],
            'crawled': item['crawled'],
            'handled': 0,
        }
        try:
            spider.mongo_col.insert(data)
        except Exception as err:
            logging.error(str(err))
        finally:
            DropItem()


class WxgzhTaskPipeline(object):
    def process_item(self, item, spider):
        data = {
            'url': item['url'],
            'task_unique_id': item['task_unique_id'],
            'unique_id': item['unique_id'],
            'summary': item['summary'],
            'date': item['date'],
            'source': item['source'],
            'origin': item['origin'],
            'type': item['type'],
            'location': item['location'],
            'crawled': item['crawled'],
        }
        try:
            spider.mongo_col.insert(data)
        except Exception as err:
            logging.error(str(err))
        finally:
            DropItem()


class WxgzhPipeline(object):
    def process_item(self, item, spider):
        try:
            spider.mongo_col.update({'unique_id': item['unique_id']}, {
                '$set': {'content': item['content'], 'title': item['title'],
                         'summary': item['summary'], 'handled': 0}
            })
        except Exception as err:
            logging.error(str(err))
        finally:
            DropItem()
