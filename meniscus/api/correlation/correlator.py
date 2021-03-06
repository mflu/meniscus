import httplib
from uuid import uuid4

import requests

import meniscus.api.correlation.correlation_exceptions as errors
from meniscus.openstack.common import timeutils
from meniscus.api.tenant.resources import MESSAGE_TOKEN
from meniscus.api.utils.request import http_request
from meniscus.data.cache_handler import ConfigCache
from meniscus.data.cache_handler import TenantCache
from meniscus.data.cache_handler import TokenCache
from meniscus.data.model.tenant import EventProducer
from meniscus.data.model.util import find_event_producer
from meniscus.data.model.util import load_tenant_from_dict
from meniscus import env


_LOG = env.get_logger(__name__)


def validate_event_message_body(body):
    """
    This method validates the on_post request body
    """

    # validate host with tenant
    if 'host' not in body.keys() or not body['host']:
        raise errors.MessageValidationError("host cannot be empty")

    if 'pname' not in body.keys() or not body['pname']:
        raise errors.MessageValidationError("pname cannot be empty")

    if 'time' not in body.keys() or not body['time']:
        raise errors.MessageValidationError("time cannot be empty")

    return True


def add_correlation_info_to_message(tenant, message):
    #match the producer by the message pname
    producer = find_event_producer(
        tenant, producer_name=message['pname'])

    #if the producer is not found, create a default producer
    if not producer:
        producer = EventProducer(_id=None, name="default", pattern="default")

    #create correlation dictionary
    correlation_dict = {
        'tenant_name': tenant.tenant_name,
        'ep_id': producer.get_id(),
        'pattern': producer.pattern,
        'durable': producer.durable,
        'encrypted': producer.encrypted,
        '@timestamp': timeutils.utcnow(),
        'sinks': producer.sinks,
        "destinations": dict()
    }

    #configure sink dispatch
    destinations = dict()
    for sink in producer.sinks:
        correlation_dict["destinations"][sink] = {
            'transaction_id': None,
            'transaction_time': None
        }

    #todo(sgonzales) persist message and create job
    if producer.durable:
        durable_job_id = str(uuid4())
        correlation_dict.update({'job_id': durable_job_id})

    message.update({
        "meniscus": {
            "tenant": tenant.tenant_id,
            "correlation": correlation_dict
        }
    })

    return message


class TenantIdentification(object):
    def __init__(self, tenant_id, message_token):
        self.tenant_id = tenant_id
        self.message_token = message_token

    def get_validated_tenant(self):
        """
        returns a validated tenant object from cache or from coordinator
        """
        token_cache = TokenCache()
        tenant_cache = TenantCache()

        #check if the token is in the cache
        token = token_cache.get_token(self.tenant_id)
        if token:
            #validate token
            if not token.validate_token(self.message_token):
                raise errors.MessageAuthenticationError(
                    'Message not authenticated, check your tenant id '
                    'and or message token for validity')

            #get the tenant object from cache
            tenant = tenant_cache.get_tenant(self.tenant_id)

            #if tenant is not in cache, ask the coordinator
            if not tenant:
                tenant = self._get_tenant_from_coordinator()
                token_cache.set_token(self.tenant_id, tenant.token)
                tenant_cache.set_tenant(tenant)
        else:
            self._validate_token_with_coordinator()

            #get tenant from coordinator
            tenant = self._get_tenant_from_coordinator()
            token_cache.set_token(self.tenant_id, tenant.token)
            tenant_cache.set_tenant(tenant)

        return tenant

    def _validate_token_with_coordinator(self):
        """
        This method calls to the coordinator to validate the message token
        """

        config_cache = ConfigCache()
        config = config_cache.get_config()

        token_header = {
            MESSAGE_TOKEN: self.message_token,
            "WORKER-ID": config.worker_id,
            "WORKER-TOKEN": config.worker_token
        }

        request_uri = "{0}/tenant/{1}/token".format(
            config.coordinator_uri, self.tenant_id)

        try:
            resp = http_request(request_uri, token_header,
                                http_verb='HEAD')

        except requests.RequestException as ex:
            _LOG.exception(ex.message)
            raise errors.CoordinatorCommunicationError

        if resp.status_code != httplib.OK:
            raise errors.MessageAuthenticationError(
                'Message not authenticated, check your tenant id '
                'and or message token for validity')

        return True

    def _get_tenant_from_coordinator(self):
        """
        This method calls to the coordinator to retrieve tenant
        """

        config_cache = ConfigCache()
        config = config_cache.get_config()

        token_header = {
            MESSAGE_TOKEN: self.message_token,
            "WORKER-ID": config.worker_id,
            "WORKER-TOKEN": config.worker_token
        }

        request_uri = "{0}/tenant/{1}".format(
            config.coordinator_uri, self.tenant_id)

        try:
            resp = http_request(request_uri, token_header,
                                http_verb='GET')

        except requests.RequestException as ex:
            _LOG.exception(ex.message)
            raise errors.CoordinatorCommunicationError

        if resp.status_code == httplib.OK:
            response_body = resp.json()
            tenant = load_tenant_from_dict(response_body['tenant'])
            return tenant

        elif resp.status_code == httplib.NOT_FOUND:
            message = 'unable to locate tenant.'
            _LOG.debug(message)
            raise errors.ResourceNotFoundError(message)
        else:
            raise errors.CoordinatorCommunicationError
