import pymongo


class MongodbClient(object):
    def __init__(self, address='localhost', port=27017):
        self.__client = pymongo.MongoClient(address, port)

    def get_client(self):
        return self.__client

    def close(self):
        client = self.get_client()
        if client is not None:
            client.close()

    def get_database(self, db_name, user_name=None, password=None):
        if user_name is not None:
            self.__client[db_name].authenticate(user_name, password)
        return self.__client[db_name]

    def get_collection(self, db, col_name):
        collect = None
        if db is not None:
            collect = db[col_name]
        return collect

    def get_collection_names(self, db_name):
        db = self.get_database(db_name)
        names = []
        if db is not None:
            names = db.collection_names()
        return names

    def clear_collection(self, db_name, collect):
        db = self.__client[db_name]
        if db is not None:
            db[collect].remove()


def main():
    import pprint
    mongodb_client = MongodbClient()
    db = mongodb_client.get_database('database_name', 'user', 'password')
    col = mongodb_client.get_collection(db, 'collection_name')
    # index
    col.create_index({"user_id": 1}, {"unique": True})
    # search
    res = col.find({'some_field.1': {'$exists': True}})  # some_field: [1, 2] or [1, 2, 3]
    res = col.find({'some_field.0': {'$exists': True}})  # some_field: [1] or [1, 2]
    res = col.find({'some_field': {'$exists': True}})  # has some_field
    res = col.find({'$and': [{'some_field.1': {'$exists': True}}, {'other_field': 0}]})

    res = col.find({'some_field': {'$regex': "value1|value2|value3"}})  # some_field: value1 or value2 or value3; return all match records
    res = col.find({}).sort({'some_field': -1}).limit(50)  # sort
    res = col.find({'some_field': {'$nin': [{'some_field': {'$regex': "some string"}}, ]}})
    res = col.find({"some_field": {'$gt': 'value'}})
    res = col.find().limit(1).sort({'$natural': -1})  # latest record
    # update
    res = col.update({'some_field': 1}, {'$set': {'some_field': 0}}, multi=True)
    res = col.update({}, {'$set': {'some_field': 0}}, multi=True)  # add filed
    res = col.update({}, {'$unset': {'some_field': 0}}, upsert=False, multi=True)
    res = col.update({'some_field': {'$regex': "value1|value2|value3"}}, {'$set': {'other_field': -1}}, multi=True)
    res = col.update({'some_field': "value1"}, {'$push': {"other_field": "value"}})  # other_field: [1] --> [1, value]
    # atomic operation
    res = col.find_one_and_update({'some_field': 'value'}, {'$set': {'other_field': 1}})
    res = col.find_one_and_replace({'some_field': 'value'}, {'other_field': 1})
    res = col.find_one_and_delete({'some_field': 'value'})
    pprint.pprint(res)


if __name__ == '__main__':
    main()
