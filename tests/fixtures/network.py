import pytest

from mdm_demo.application.use_cases.network import NetworkUseCases
from mdm_demo.application.use_cases.network_log import NetworkLogUseCases
from mdm_demo.composition.network import build_services
from mdm_demo.infrastructure.pagination.network_cursor import SignedNetworkCursor


@pytest.fixture
def network_cursor_codec(signing_key) -> SignedNetworkCursor:
    return SignedNetworkCursor(signing_key)


@pytest.fixture
def network_service(runtime_resources) -> NetworkUseCases:
    return build_services(runtime_resources)[0]


@pytest.fixture
def network_log_service(runtime_resources) -> NetworkLogUseCases:
    return build_services(runtime_resources)[1]
