import falcon

from meniscus.api.version.resources import VersionResource
from meniscus.api.pairing.resources import PairingConfigurationResource
from meniscus import env


_LOG = env.get_logger(__name__)


def start_up():
    # Resources
    versions = VersionResource()
    configuration = PairingConfigurationResource()

    # Routing
    application = api = falcon.API()

    api.add_route('/', versions)
    api.add_route('/v1/pairing/configure', configuration)

    return application
