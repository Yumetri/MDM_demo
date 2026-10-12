import pytest

from mdm_demo.application.use_cases.category import CategoryUseCases
from mdm_demo.application.use_cases.category_log import CategoryLogUseCases
from mdm_demo.composition.category import build_services
from mdm_demo.infrastructure.pagination.category_cursor import SignedCategoryCursor


@pytest.fixture
def category_cursor_codec(signing_key) -> SignedCategoryCursor:
    return SignedCategoryCursor(signing_key)


@pytest.fixture
def category_service(runtime_resources) -> CategoryUseCases:
    return build_services(runtime_resources)[0]


@pytest.fixture
def category_log_service(runtime_resources) -> CategoryLogUseCases:
    return build_services(runtime_resources)[1]
