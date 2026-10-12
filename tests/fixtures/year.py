import pytest

from mdm_demo.application.use_cases.year import YearUseCases
from mdm_demo.application.use_cases.year_log import YearLogUseCases
from mdm_demo.composition.year import build_services
from mdm_demo.infrastructure.pagination.year_cursor import SignedYearCursor


@pytest.fixture
def year_cursor_codec(signing_key) -> SignedYearCursor:
    return SignedYearCursor(signing_key)


@pytest.fixture
def year_service(runtime_resources) -> YearUseCases:
    return build_services(runtime_resources)[0]


@pytest.fixture
def year_log_service(runtime_resources) -> YearLogUseCases:
    return build_services(runtime_resources)[1]
