import pytest

from mdm_demo.application.use_cases.brand import BrandUseCases
from mdm_demo.application.use_cases.brand_log import BrandLogUseCases
from mdm_demo.composition.brand import build_services
from mdm_demo.infrastructure.pagination.brand_cursor import SignedBrandCursor


@pytest.fixture
def brand_cursor_codec(signing_key) -> SignedBrandCursor:
    return SignedBrandCursor(signing_key)


@pytest.fixture
def brand_service(runtime_resources) -> BrandUseCases:
    return build_services(runtime_resources)[0]


@pytest.fixture
def brand_log_service(runtime_resources) -> BrandLogUseCases:
    return build_services(runtime_resources)[1]
