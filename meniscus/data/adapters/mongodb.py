from pymongo import MongoClient

from oslo.config import cfg
from meniscus.config import get_config
from meniscus.data.handler import *

# MongoDB configuration options
_mongodb_group = cfg.OptGroup(name='mongodb', title='MongoDB Options')
get_config().register_group(_mongodb_group)

_MONGODB_OPTIONS = [
    cfg.ListOpt('mongo_servers',
               default=['localhost:27017'],
               help="""MongoDB servers to connect to.
                    """
               ),
   cfg.StrOpt('database',
               default='test',
               help="""MongoDB database to use.
                    """
               ),
   cfg.StrOpt('username',
               default='',
               help="""MongoDB username to use when authenticating.
                       If this value is left unset, then authentication
                       against the MongoDB will not be utilized.
                    """,
               secret=True
               ),
   cfg.StrOpt('password',
               default='',
               help="""MongoDB password to use when authenticating.
                       If this value is left unset, then authentication
                       against the MongoDB will not be utilized.
                    """,
               secret=True
               )
]

get_config().register_opts(_MONGODB_OPTIONS, group=_mongodb_group)


class MongoDatasourceHandler(DatasourceHandler):

    def __init__(self, conf):
        self.mongo_servers = conf.mongodb.mongo_servers
        self.database_name = conf.mongodb.database
        self.username = conf.mongodb.username
        self.password = conf.mongodb.password

    def _check_connection(self):
        if self.status != STATUS_CONNECTED:
            raise DatabaseHandlerError('Database not connected.')

    def connect(self):
        self.connection = MongoClient(self.mongo_servers, slave_okay=True)
        self.database = self.connection[self.database_name]

        if self.username and self.password:
            self.database.authenticate(self.username, self.password)
        
        self.status = STATUS_CONNECTED

    def close(self):
        self.connection.close()
        self.status = STATUS_CLOSED

    def find(self, object_name, query_filter=dict()):
        self._check_connection()
        return self.database[object_name].find(query_filter)

    def find_one(self, object_name, query_filter=dict()):
        self._check_connection()
        return self.database[object_name].find_one(query_filter)

    def put(self, object_name, document=dict()):
        self._check_connection()
        self.database[object_name].insert(document)

    def delete(self, object_name, query_filter=dict()):
        self.database[object_name].remove(query_filter, True)


# Registers this handler and make it available for use
def register_mongodb():
    register_handler('mongodb', MongoDatasourceHandler)
