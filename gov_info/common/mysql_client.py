# -*- coding: utf-8 -*-
import time
import logging

import pymysql


class MysqlClient:
    def __init__(self, user, password, database, host='localhost', port=3306, charset='utf8'):
        self.mysql_cur = None
        self.mysql_conn = None
        self.user = user
        self.password = password
        self.database = database
        self.host = host
        self.port = int(port)
        self.charset = charset

    def connect(self):
        try:
            self.mysql_conn = pymysql.connect(host=self.host,
                                              port=self.port,
                                              user=self.user,
                                              passwd=self.password,
                                              db=self.database,
                                              charset=self.charset)
            self.mysql_conn.autocommit(True)
            self.mysql_cur = self.mysql_conn.cursor()

        except Exception as err:
            # logging.error('数据库连接失败！')
            raise Exception(err)

    def close(self):
        self.mysql_cur.close()
        self.mysql_conn.close()

    def insert(self, proc, args):
        self.connect()
        try:
            self.mysql_cur.callproc(proc, args)

        except Exception as err:
            logging.error('存储过程{proc}调用失败, 参数:{args}'.format(proc=proc, args=args))
            raise Exception(err)
        finally:
            self.close()

    def execute_by_sql(self, sql, args='', operate='select', retry=5):
        status, result, error = 0, None, None
        while retry > 0:
            self.connect()
            try:
                if args == '':
                    self.mysql_cur.execute(sql)
                else:
                    self.mysql_cur.execute(sql, args)
            except Exception as err:
                retry -= 1
                error = err
            else:
                status = 1
                if operate.lower() == 'select':
                    result = self.mysql_cur.fetchall()
                break
            finally:
                self.close()
            time.sleep(1)

        return status, result, error

    def select(self, proc, args=''):
        self.connect()
        try:
            if args:
                self.mysql_cur.callproc(proc, args)
            else:
                self.mysql_cur.callproc(proc)
            data = self.mysql_cur.fetchall()
            return data
        except Exception as err:
            logging.error('存储过程{proc}调用失败, 参数:{args}'.format(proc=proc, args=args))
            raise Exception(err)
        finally:
            self.close()

    def update(self, proc, args):
        self.connect()
        try:
            self.mysql_cur.callproc(proc, args)
        except Exception as err:
            logging.error('存储过程{proc}调用失败, 参数:{args}'.format(proc=proc, args=args))
            raise Exception(err)
        finally:
            self.close()

    def transaction(self, lst):
        self.connect()
        try:
            for sql, args in lst:
                self.mysql_cur.execute(sql, args)
            self.mysql_cur.close()
            self.mysql_conn.commit()
        except Exception as err:
            self.mysql_conn.rollback()
            raise Exception(err)
        finally:
            self.mysql_conn.close()


def main():
    mysql_client = MysqlClient('test', 'test', 'TestDb')


if __name__ == '__main__':
    pass
