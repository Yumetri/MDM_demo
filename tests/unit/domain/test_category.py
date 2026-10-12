import operator
from collections.abc import MutableMapping
from dataclasses import FrozenInstanceError
from typing import cast
from unicodedata import normalize
from uuid import uuid4

import pytest

from mdm_demo.domain.entities.category import Category
from mdm_demo.domain.entities.category_log import CategoryLog
from mdm_demo.domain.errors import AutoCodeUnavailable
from mdm_demo.domain.errors.category import InvalidCategoryValue
from mdm_demo.domain.value_objects.category_code import CategoryCode
from mdm_demo.domain.value_objects.category_name import CategoryName


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (" smartphone ", "SMARTPHONE"),
        ("스마트폰", "스마트폰"),
        (normalize("NFD", "스마트폰"), "스마트폰"),
        (" straße ", "STRASSE"),
        ("  New  Zealand\n", "NEW  ZEALAND"),
        ("a", "A"),
        ("ß" * 50, "SS" * 50),
    ],
)
def test_name_normalization(raw, expected):
    assert CategoryName(raw).value == expected
    assert CategoryName(raw) == CategoryName(expected)


@pytest.mark.parametrize("raw", ["", " \t\n", "a" * 101, "ß" * 51, "a\x00b", "\ud800", "\udfff"])
def test_invalid_name(raw):
    with pytest.raises(InvalidCategoryValue):
        CategoryName(raw)


@pytest.mark.parametrize("raw", ["", " ", "AB", "ABCD", "K!1", "ＫＯＲ", "KOR", "K R", "ÄBC"])
def test_invalid_code(raw):
    with pytest.raises(InvalidCategoryValue):
        CategoryCode(raw)


def test_entity_identity_immutable_code_and_normalized_noop():
    category = Category.create(" smartphone ", " sma ")
    assert category.code == CategoryCode("SMA")
    same = Category(
        category.id, CategoryName("OTHER"), category.code, category.created_at, category.updated_at
    )
    assert same == category and hash(same) == hash(category)
    assert category != Category.create("SMARTPHONE", "SMA")
    before = category.updated_at
    assert not category.rename(" smartphone ")
    assert category.updated_at == before
    assert category.rename("스마트폰")
    assert not category.rename(normalize("NFD", "스마트폰"))
    assert category.code.value == "SMA"
    for attribute in ("code", "name"):
        with pytest.raises(FrozenInstanceError):
            setattr(category, attribute, CategoryCode("NEW"))


def test_log_snapshot_copy_and_immutability():
    category = Category.create("Smartphone", "SMA")
    snapshot = category.snapshot()
    log = CategoryLog.record(category.id, "create", uuid4(), None, snapshot)
    snapshot["name"] = "CHANGED"
    assert log.after is not None and log.after["name"] == "SMARTPHONE"
    with pytest.raises(TypeError):
        operator.setitem(cast(MutableMapping[str, str], log.after), "name", "CHANGED")
    with pytest.raises(ValueError):
        CategoryLog.record(category.id, "delete", uuid4(), None, None)


@pytest.mark.parametrize(
    ("name", "expected"),
    [("Smartphone", "SMA"), ("분류 s24", "S24"), ("  Straße ", "STR"), ("A-1 b", "A1B")],
)
def test_code_from_normalized_name(name, expected):
    category = Category.create(name)
    assert category.code.value == expected


@pytest.mark.parametrize("name", ["스마트폰", "A1"])
def test_auto_code_unavailable(name):
    with pytest.raises(AutoCodeUnavailable):
        Category.create(name)


def test_numeric_code_and_nfc_length_after_normalization():
    assert CategoryCode(" n01 ").value == "N01"
    assert CategoryName(normalize("NFD", "가" * 100)).value == "가" * 100
