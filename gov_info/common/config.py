import platform

MONGODB_SERVER = 'localhost'
MONGODB_PORT = 27017
MONGODB_DB = 'Test'
MONGODB_COLLECTION = 'test'

MYSQL_SERVER = 'localhost'
MYSQL_PORT = 3306
MYSQL_DB = ''
MYSQL_TABLE = ''
MYSQL_USER = ''
MYSQL_PASSWORD = ''

REDIS_SERVER = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 15


try:
    if platform.system().lower() == 'linux':
        from gov_info.common.local_config import *
except:
    pass
