from dataclasses import FrozenInstanceError, replace
from typing import Any, cast
from uuid import uuid4

import pytest

from mdm_demo.domain.entities.memory import Memory
from mdm_demo.domain.entities.memory_log import MemoryLog
from mdm_demo.domain.errors.memory import InvalidMemoryValue
from mdm_demo.domain.value_objects.memory_size import MemorySize


@pytest.mark.parametrize(
    ("capacity", "unit", "code", "gb"),
    [
        (1, "GB", "1GB", 1),
        (256, " gb ", "256GB", 256),
        (1, "TB", "1TB", 1000),
        (2147483647, "tb", "2147483647TB", 2147483647000),
    ],
)
def test_size_normalization_boundaries_and_exact_conversion(capacity, unit, code, gb):
    size = MemorySize(capacity, unit)
    assert size.code == code and size.capacity_gb == gb
    with pytest.raises(FrozenInstanceError):
        cast(Any, size).capacity = 2


@pytest.mark.parametrize("capacity", [0, -1, 2147483648, "256", 256.0, 0.5, True, False, None, []])
def test_invalid_capacity_is_rejected_without_coercion(capacity):
    with pytest.raises(InvalidMemoryValue) as error:
        MemorySize(capacity, "GB")
    assert error.value.field == "capacity"


@pytest.mark.parametrize("unit", ["", "  ", "G B", "MB", "GiB", "ＴＢ", None, 1, True])
def test_invalid_unit(unit):
    with pytest.raises(InvalidMemoryValue) as error:
        MemorySize(256, unit)
    assert error.value.field == "unit"


def test_identity_and_representation_changes_preserve_before_snapshot():
    memory = Memory.create(1, "tb")
    before = memory.snapshot()
    identity, created, updated = memory.id, memory.created_at, memory.updated_at
    assert not memory.change_size(1, " TB ")
    assert memory.updated_at == updated
    assert memory.change_size(1000, "GB")
    assert memory.size.capacity_gb == 1000
    assert memory.id == identity and memory.created_at == created
    assert memory.size.code == "1000GB"
    assert before["capacity"] == 1 and before["unit"] == "TB"
    assert memory == replace(memory, size=MemorySize(512, "GB"))
    assert memory != Memory.create(1000, "GB")
    with pytest.raises(FrozenInstanceError):
        cast(Any, memory).size = MemorySize(512, "GB")


def test_log_snapshots_copy_and_preserve_integer():
    memory = Memory.create(256, "GB")
    snapshot = memory.snapshot()
    log = MemoryLog.record(memory.id, "create", uuid4(), None, snapshot)
    snapshot["capacity"] = 512
    assert log.after is not None and log.after["capacity"] == 256
    assert type(log.after["capacity"]) is int
    with pytest.raises(TypeError):
        cast(dict[str, str | int], log.after)["capacity"] = 1024
    with pytest.raises(ValueError):
        MemoryLog.record(memory.id, "delete", uuid4(), None, None)
