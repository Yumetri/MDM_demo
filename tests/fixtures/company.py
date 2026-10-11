import pytest

from mdm_demo.application.use_cases.company import CompanyUseCases
from mdm_demo.application.use_cases.company_log import CompanyLogUseCases
from mdm_demo.composition.company import build_services
from mdm_demo.infrastructure.pagination.company_cursor import SignedCompanyCursor


@pytest.fixture
def cursor_codec(signing_key) -> SignedCompanyCursor:
    return SignedCompanyCursor(signing_key)


@pytest.fixture
def service(runtime_resources) -> CompanyUseCases:
    return build_services(runtime_resources)[0]


@pytest.fixture
def log_service(runtime_resources) -> CompanyLogUseCases:
    return build_services(runtime_resources)[1]
