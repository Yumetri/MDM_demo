import operator
from collections.abc import MutableMapping
from dataclasses import FrozenInstanceError
from typing import cast
from unicodedata import normalize
from uuid import uuid4

import pytest

from mdm_demo.domain.entities.country import Country
from mdm_demo.domain.entities.country_log import CountryLog
from mdm_demo.domain.errors import InvalidCountryValue
from mdm_demo.domain.value_objects.country_code import CountryCode
from mdm_demo.domain.value_objects.country_name import CountryName


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (" korea ", "KOREA"),
        ("대한민국", "대한민국"),
        (normalize("NFD", "대한민국"), "대한민국"),
        (" straße ", "STRASSE"),
        ("  New  Zealand\n", "NEW  ZEALAND"),
        ("a", "A"),
        ("ß" * 50, "SS" * 50),
    ],
)
def test_name_normalization(raw, expected):
    assert CountryName(raw).value == expected
    assert CountryName(raw) == CountryName(expected)


@pytest.mark.parametrize("raw", ["", " \t\n", "a" * 101, "ß" * 51, "a\x00b", "\ud800", "\udfff"])
def test_invalid_name(raw):
    with pytest.raises(InvalidCountryValue):
        CountryName(raw)


@pytest.mark.parametrize("raw", ["", " ", "AB", "ABCD", "K01", "ＫＯＲ", "KOR", "K R", "ÄBC"])
def test_invalid_code(raw):
    with pytest.raises(InvalidCountryValue):
        CountryCode(raw)


def test_entity_identity_immutable_code_and_normalized_noop():
    country = Country.create(" korea ", " kor ")
    assert country.code == CountryCode("KOR")
    same = Country(
        country.id, CountryName("OTHER"), country.code, country.created_at, country.updated_at
    )
    assert same == country and hash(same) == hash(country)
    assert country != Country.create("KOREA", "KOR")
    before = country.updated_at
    assert not country.rename(" korea ")
    assert country.updated_at == before
    assert country.rename("대한민국")
    assert not country.rename(normalize("NFD", "대한민국"))
    assert country.code.value == "KOR"
    for attribute in ("code", "name"):
        with pytest.raises(FrozenInstanceError):
            setattr(country, attribute, CountryCode("NEW"))


def test_log_snapshot_copy_and_immutability():
    country = Country.create("Korea", "KOR")
    snapshot = country.snapshot()
    log = CountryLog.record(country.id, "create", uuid4(), None, snapshot)
    snapshot["name"] = "CHANGED"
    assert log.after is not None and log.after["name"] == "KOREA"
    with pytest.raises(TypeError):
        operator.setitem(cast(MutableMapping[str, str], log.after), "name", "CHANGED")
    with pytest.raises(ValueError):
        CountryLog.record(country.id, "delete", uuid4(), None, None)
