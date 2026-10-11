import pytest

from mdm_demo.application.use_cases.model import ModelUseCases
from mdm_demo.application.use_cases.model_log import ModelLogUseCases
from mdm_demo.composition.model import build_services
from mdm_demo.infrastructure.pagination.model_cursor import SignedModelCursor


@pytest.fixture
def model_cursor_codec(signing_key) -> SignedModelCursor:
    return SignedModelCursor(signing_key)


@pytest.fixture
def model_service(runtime_resources) -> ModelUseCases:
    return build_services(runtime_resources)[0]


@pytest.fixture
def model_log_service(runtime_resources) -> ModelLogUseCases:
    return build_services(runtime_resources)[1]
