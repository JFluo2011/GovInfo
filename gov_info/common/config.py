import platform

MONGODB_SERVER = 'localhost'
MONGODB_PORT = 27017
MONGODB_DB = 'Test'
MONGODB_COLLECTION = 'test'

MYSQL_SERVER = 'localhost'
MYSQL_PORT = 3306
MYSQL_DB = ''
MYSQL_TABLE_NEWS = ''
MYSQL_TABLE_NEWS_TAG = ''
MYSQL_TABLE_TAG = ''
MYSQL_USER = ''
MYSQL_PASSWORD = ''

REDIS_HOST = 'localhost'
REDIS_PORT = 6379

REDIS_PARAMS = {
    # 'password': '',
    'db': 15,
}

USER_REDIS = {
    'host': REDIS_HOST,
    'port': REDIS_PORT,
    'db': REDIS_PARAMS['db'],
    # 'password': REDIS_PARAMS['password'],
    'socket_timeout': 3
}


try:
    if platform.system().lower() == 'linux':
        from gov_info.common.local_config import *
except:
    pass
