import sys
sys.path.append('../..')

import os
import time
import logging

from gov_info.settings import MONGODB_COLLECTION
from gov_info.settings import MYSQL_SERVER, MYSQL_PORT, MYSQL_DB, MYSQL_USER, MYSQL_PASSWORD
from gov_info.settings import MYSQL_TABLE_NEWS, MYSQL_TABLE_NEWS_TAG, MYSQL_TABLE_TAG

from gov_info.common.utils import get_col, setup_log
from gov_info.common.mysql_client import MysqlClient
from gov_info.common.mongodb_client import PyMongoError


class DataHandler:
    def __init__(self):
        self.mongo_col = get_col(MONGODB_COLLECTION)
        self.mysql_Client = MysqlClient(
            host=MYSQL_SERVER,
            port=MYSQL_PORT,
            database=MYSQL_DB,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD
        )

    def handle(self):
        while True:
            task = self.get_handle_task()
            if task is None:
                logging.info('no more task to handle')
                self.mongo_col.update({'$and': [{'crawled': 1}, {'handled': {'$ne': 1}}]},
                                      {'$set': {'handled': 0}}, multi=True)
                time.sleep(60)
                continue
            status = self.handle_to_mysql(task)
            self.update_handle_task(task, status)
            logging.info(f'news {task["url"]} had handled')
            time.sleep(1)

    def get_handle_task(self, retry=5):
        task = None
        while retry > 0:
            try:
                task = self.mongo_col.find_one_and_update(
                    {'$and': [{'crawled': 1}, {'handled': 0}]}, {'$set': {'handled': 2}})
            except PyMongoError as err:
                logging.error(f'{str(err)}, {retry} times to retry')
                retry -= 1
                self.mongo_col = get_col(MONGODB_COLLECTION)
            else:
                break
            time.sleep(1)
        else:
            logging.error(f'{str(err)}, max times retry')
        return task

    def update_handle_task(self, task, status, retry=5):
        while retry > 0:
            try:
                self.mongo_col.update({'_id': task['_id']}, {'$set': {'handled': status}})
            except Exception as err:
                logging.error(f'{str(err)}, {retry} times to retry')
                retry -= 1
                self.mongo_col = get_col(MONGODB_COLLECTION)
            else:
                break
            time.sleep(1)
        else:
            logging.error(f'update handle task failed, {task["_id"]}--{status}, max times retry')

    def handle_to_mysql(self, task, retry=5):
        status = 1
        news_id, tag_id = None, None
        try:
            self.insert_news(task, retry=retry)
            news_id = self.select_news_id(task, retry=retry)
            tag_id = self.select_tag_id(task, retry=retry)
            self.insert_tags(news_id, tag_id, retry=retry)
        except Exception as err:
            status = 0
            if news_id is not None:
                self.delete_news(news_id, retry=retry)

        return status

    def insert_news(self, task, retry=5):
        keys = 'mongodb_id, origin, summary, title, content, source, create_time, location, type'
        values = ','.join(['%s' for _ in keys.split(',')])
        sql = f"""insert into {MYSQL_TABLE_NEWS}({keys}) values ({values});"""
        mongodb_id = str(task['_id'])
        date = task['date']
        args = [
            mongodb_id,
            task['origin'],
            task['summary'],
            task['title'],
            task['content'],
            task['source'],
            date,
            task['location'],
            task['type'],
        ]
        self.execute(sql, args=args, operate='select', retry=retry)

    def insert_tags(self, news_id, tag_id, retry=5):
        keys = 'news_id, tag_id'
        values = ','.join(['%s' for _ in keys.split(',')])
        sql = f"""insert into {MYSQL_TABLE_NEWS_TAG}({keys}) values ({values});"""
        args = [
            news_id,
            tag_id
        ]
        self.execute(sql, args=args, operate='select', retry=retry)

    def select_news_id(self, task, retry=5):
        mongodb_id = str(task['_id'])
        sql = f'SELECT id from {MYSQL_TABLE_NEWS} WHERE mongodb_id="{mongodb_id}";'
        result = self.execute(sql, args='', operate='select', retry=retry)
        return result[0][0]

    def select_tag_id(self, task, retry=5):
        location = task['location']
        sql = f'SELECT id from {MYSQL_TABLE_TAG} WHERE name="{location}";'
        result = self.execute(sql, args='', operate='select', retry=retry)

        return result[0][0]

    def delete_news(self, news_id, retry=5):
        sql = f'delete from {MYSQL_TABLE_NEWS} WHERE id="{news_id}";'
        try:
            self.execute(sql, args='', operate='delete', retry=retry)
        except:
            pass

    def execute(self, sql, args, operate, retry=5):
        status, result, error = self.mysql_Client.execute_by_sql(sql, args, operate=operate, retry=retry)
        if status != 1:
            logging.error(f'insert task failed: {sql}, max times retry, last error: {str(error)}')
            raise error
        return result


def main():
    setup_log(logging.INFO, os.path.join(os.path.abspath('.'), 'logs', 'data_handler.log'))
    data_handler = DataHandler()
    data_handler.handle()


if __name__ == '__main__':
    main()

