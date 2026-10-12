from dataclasses import FrozenInstanceError
from typing import cast
from uuid import uuid4

import pytest

from mdm_demo.domain.entities.year import Year
from mdm_demo.domain.entities.year_log import YearLog
from mdm_demo.domain.errors.year import InvalidYearValue
from mdm_demo.domain.value_objects.year_code import YearCode
from mdm_demo.domain.value_objects.year_value import YearValue


@pytest.mark.parametrize("value", [1900, 2024, 2999])
def test_auto_code_identity_and_change(value):
    entity = Year.create(value)
    assert entity.code.value == str(value)
    assert type(entity.snapshot()["year"]) is int
    before = entity.snapshot()
    timestamp = entity.updated_at
    assert entity.change_year(value) is False
    assert entity.updated_at == timestamp
    changed = 2025 if value != 2025 else 2026
    assert entity.change_year(changed)
    assert entity.id == before["id"] or str(entity.id) == before["id"]
    assert entity.code.value == str(changed)
    assert entity.created_at == timestamp
    assert entity == Year(entity.id, entity.year, entity.code, entity.created_at, entity.updated_at)
    assert entity != Year.create(changed)


@pytest.mark.parametrize("value", [1899, 3000, "2024", 2024.0, True, False, None])
def test_strict_value_validation(value):
    with pytest.raises(InvalidYearValue):
        YearValue(value)
    entity = Year.create(2024)
    before = entity.snapshot()
    with pytest.raises(InvalidYearValue):
        entity.change_year(value)
    assert entity.snapshot() == before


def test_immutable_values_and_consistent_code():
    with pytest.raises(FrozenInstanceError):
        YearValue.__setattr__(YearValue(2024), "value", 2025)
    entity = Year.create(2024)
    with pytest.raises(InvalidYearValue):
        Year(entity.id, entity.year, YearCode("2025"), entity.created_at, entity.updated_at)
    for code in ["202", "20240", "２０２４", " 2024", "1899", "3000"]:
        with pytest.raises(InvalidYearValue):
            YearCode(code)


def test_log_snapshots_are_copied_immutable_and_typed():
    entity = Year.create(2024)
    snapshot = entity.snapshot()
    log = YearLog.record(entity.id, "create", uuid4(), None, snapshot)
    snapshot["year"] = 2025
    assert log.after is not None
    assert log.after["year"] == 2024
    with pytest.raises(TypeError):
        cast(dict[str, str | int], log.after)["year"] = 2025
    with pytest.raises(ValueError):
        YearLog.record(entity.id, "delete", uuid4(), None, None)
