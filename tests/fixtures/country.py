import pytest

from mdm_demo.application.use_cases.country import CountryUseCases
from mdm_demo.application.use_cases.country_log import CountryLogUseCases
from mdm_demo.composition.country import build_services
from mdm_demo.infrastructure.pagination.country_cursor import SignedCountryCursor


@pytest.fixture
def country_cursor_codec(signing_key) -> SignedCountryCursor:
    return SignedCountryCursor(signing_key)


@pytest.fixture
def country_service(runtime_resources) -> CountryUseCases:
    return build_services(runtime_resources)[0]


@pytest.fixture
def country_log_service(runtime_resources) -> CountryLogUseCases:
    return build_services(runtime_resources)[1]
