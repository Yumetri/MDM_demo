import operator
from collections.abc import MutableMapping
from dataclasses import FrozenInstanceError
from typing import cast
from uuid import uuid4

import pytest

from mdm_demo.domain.entities.model import Model
from mdm_demo.domain.entities.model_log import ModelLog
from mdm_demo.domain.errors import AutoCodeUnavailable
from mdm_demo.domain.errors.model import InvalidModelValue
from mdm_demo.domain.value_objects.model_code import ModelCode
from mdm_demo.domain.value_objects.model_name import ModelName


@pytest.mark.parametrize(
    ("name", "code"),
    [
        ("Samsung", "SAM"),
        ("LG Electronics", "LGE"),
        ("3M Korea", "3MK"),
        ("한A🙂b 1C", "AB1"),
        ("ＡＢＣabc", "ABC"),
    ],
)
def test_auto_code(name, code):
    assert Model.create(name).code.value == code


@pytest.mark.parametrize("name", ["삼성전자", "LG", "ＡＢＣ", "ééé"])
def test_auto_code_needs_three_ascii_letters(name):
    with pytest.raises(AutoCodeUnavailable):
        Model.create(name)


@pytest.mark.parametrize("code", ["", " ", "AB", "ABCD", "ÄBC"])
def test_manual_code_rejects_invalid_format(code):
    with pytest.raises(InvalidModelValue):
        ModelCode(code)


def test_name_and_code_value_semantics():
    assert ModelName("  삼성  전자\n") == ModelName("삼성  전자")
    assert ModelCode("aBc") == ModelCode("ABC")
    assert Model.create("삼성", "abc").code.value == "ABC"
    assert len(ModelName("가" * 100).value) == 100


@pytest.mark.parametrize("name", ["", " \t\n", "a" * 101, "a\x00b", "ABC\ud800", "ABC\udfff"])
def test_name_boundaries(name):
    with pytest.raises(InvalidModelValue):
        ModelName(name)


def test_identity_immutable_code_and_rename():
    model = Model.create("Samsung")
    same_id = Model(model.id, ModelName("Other"), model.code, model.created_at, model.updated_at)
    assert model == same_id
    assert model != Model.create("Samsung")
    assert hash(model) == hash(same_id)
    initial_time = model.updated_at
    assert not model.rename("  Samsung  ")
    assert model.updated_at == initial_time
    assert model.rename("Samsung Electronics")
    assert model.code.value == "SAM"
    for target, attribute, value in [
        (model, "code", ModelCode("NEW")),
        (model.name, "value", "bypass"),
    ]:
        with pytest.raises(FrozenInstanceError):
            setattr(target, attribute, value)


def test_log_snapshots_are_copied_and_immutable():
    model = Model.create("Samsung")
    snapshot = model.snapshot()
    log = ModelLog.record(model.id, "create", uuid4(), None, snapshot)
    snapshot["name"] = "changed"
    assert log.after is not None and log.after["name"] == "Samsung"
    with pytest.raises(TypeError):
        operator.setitem(cast(MutableMapping[str, str], log.after), "name", "changed")
    with pytest.raises(ValueError):
        ModelLog.record(model.id, "delete", uuid4(), None, None)


@pytest.mark.parametrize("code", [" s24 ", "\ts24\n", "\u3000s24\u3000"])
def test_trimmed_alphanumeric_code(code):
    assert ModelCode(code).value == "S24"


@pytest.mark.parametrize(
    ("name", "code"),
    [("Galaxy S24", "GAL"), ("iPhone 16", "IPH"), ("갤럭시 S24", "S24"), ("123", "123")],
)
def test_product_auto_codes(name, code):
    assert Model.create(name).code.value == code
