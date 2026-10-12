import pytest

from mdm_demo.application.use_cases.memory import MemoryUseCases
from mdm_demo.application.use_cases.memory_log import MemoryLogUseCases
from mdm_demo.composition.memory import build_services
from mdm_demo.infrastructure.pagination.memory_cursor import SignedMemoryCursor


@pytest.fixture
def memory_cursor_codec(signing_key) -> SignedMemoryCursor:
    return SignedMemoryCursor(signing_key)


@pytest.fixture
def memory_service(runtime_resources) -> MemoryUseCases:
    return build_services(runtime_resources)[0]


@pytest.fixture
def memory_log_service(runtime_resources) -> MemoryLogUseCases:
    return build_services(runtime_resources)[1]
