MONGODB_SERVER = 'localhost'
MONGODB_PORT = 27017
MONGODB_DB = 'Test'
MONGODB_COLLECTION = 'test'

REDIS_SERVER = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0


try:
    from gov_info.common.local_config import *
except:
    pass
