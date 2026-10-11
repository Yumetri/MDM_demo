import operator
from collections.abc import MutableMapping
from dataclasses import FrozenInstanceError
from typing import cast
from uuid import uuid4

import pytest

from mdm_demo.domain.entities.brand import Brand
from mdm_demo.domain.entities.brand_log import BrandLog
from mdm_demo.domain.errors import AutoCodeUnavailable
from mdm_demo.domain.errors.brand import InvalidBrandValue
from mdm_demo.domain.value_objects.brand_code import BrandCode
from mdm_demo.domain.value_objects.brand_name import BrandName


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
    assert Brand.create(name).code.value == code


@pytest.mark.parametrize("name", ["삼성전자", "LG", "ＡＢＣ", "ééé"])
def test_auto_code_needs_three_ascii_letters(name):
    with pytest.raises(AutoCodeUnavailable):
        Brand.create(name)


@pytest.mark.parametrize("code", ["", " ", "AB", "ABCD", "ÄBC"])
def test_manual_code_rejects_invalid_format(code):
    with pytest.raises(InvalidBrandValue):
        BrandCode(code)


def test_name_and_code_value_semantics():
    assert BrandName("  삼성  전자\n") == BrandName("삼성  전자")
    assert BrandCode("aBc") == BrandCode("ABC")
    assert Brand.create("삼성", "abc").code.value == "ABC"
    assert len(BrandName("가" * 100).value) == 100


@pytest.mark.parametrize("name", ["", " \t\n", "a" * 101, "a\x00b", "ABC\ud800", "ABC\udfff"])
def test_name_boundaries(name):
    with pytest.raises(InvalidBrandValue):
        BrandName(name)


def test_identity_immutable_code_and_rename():
    brand = Brand.create("Samsung")
    same_id = Brand(brand.id, BrandName("Other"), brand.code, brand.created_at, brand.updated_at)
    assert brand == same_id
    assert brand != Brand.create("Samsung")
    assert hash(brand) == hash(same_id)
    initial_time = brand.updated_at
    assert not brand.rename("  Samsung  ")
    assert brand.updated_at == initial_time
    assert brand.rename("Samsung Electronics")
    assert brand.code.value == "SAM"
    for target, attribute, value in [
        (brand, "code", BrandCode("NEW")),
        (brand.name, "value", "bypass"),
    ]:
        with pytest.raises(FrozenInstanceError):
            setattr(target, attribute, value)


def test_log_snapshots_are_copied_and_immutable():
    brand = Brand.create("Samsung")
    snapshot = brand.snapshot()
    log = BrandLog.record(brand.id, "create", uuid4(), None, snapshot)
    snapshot["name"] = "changed"
    assert log.after is not None and log.after["name"] == "Samsung"
    with pytest.raises(TypeError):
        operator.setitem(cast(MutableMapping[str, str], log.after), "name", "changed")
    with pytest.raises(ValueError):
        BrandLog.record(brand.id, "delete", uuid4(), None, None)


@pytest.mark.parametrize("code", [" s24 ", "\ts24\n", "\u3000s24\u3000"])
def test_trimmed_alphanumeric_code(code):
    assert BrandCode(code).value == "S24"


@pytest.mark.parametrize(
    ("name", "code"),
    [("Galaxy S24", "GAL"), ("iPhone 16", "IPH"), ("갤럭시 S24", "S24"), ("123", "123")],
)
def test_product_auto_codes(name, code):
    assert Brand.create(name).code.value == code
