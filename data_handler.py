import sys
sys.path.append('../..')

import os
import time
import logging

from gov_info.settings import MONGODB_COLLECTION
from gov_info.settings import MYSQL_SERVER, MYSQL_PORT, MYSQL_DB, MYSQL_TABLE, MYSQL_USER, MYSQL_PASSWORD

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
        status = 0
        sql = f"""insert into {MYSQL_TABLE}(summary, title, content, source, create_time) values (%s,%s,%s,%s,%s);"""
        date = task['date']
        args = [task['summary'], task['title'], task['content'], task['source'], date]
        while retry > 0:
            try:
                self.mysql_Client.insert_by_sql(sql, args=args)
            except Exception as err:
                logging.error(f'{str(err)}, {retry} times to retry')
                retry -= 1
            else:
                status = 1
                break
            time.sleep(1)
        else:
            logging.error(f'update handle task failed, {task["_id"]}--{sql}, max times retry')

        return status


def main():
    setup_log(logging.INFO, os.path.join(os.path.abspath('.'), 'logs', 'data_handler.log'))
    data_handler = DataHandler()
    data_handler.handle()


if __name__ == '__main__':
    main()

