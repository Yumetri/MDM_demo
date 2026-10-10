import operator
from collections.abc import MutableMapping
from dataclasses import FrozenInstanceError
from typing import cast
from uuid import uuid4

import pytest

from mdm_demo.domain.entities.company import Company
from mdm_demo.domain.entities.company_log import CompanyLog
from mdm_demo.domain.errors import AutoCodeUnavailable, InvalidCompanyValue
from mdm_demo.domain.value_objects.company_code import CompanyCode
from mdm_demo.domain.value_objects.company_name import CompanyName


@pytest.mark.parametrize(
    ("name", "code"),
    [
        ("Samsung", "SAM"),
        ("LG Electronics", "LGE"),
        ("3M Korea", "MKO"),
        ("한A🙂b 1C", "ABC"),
        ("ＡＢＣabc", "ABC"),
    ],
)
def test_auto_code(name, code):
    assert Company.create(name).code.value == code


@pytest.mark.parametrize("name", ["삼성전자", "LG", "ＡＢＣ", "ééé"])
def test_auto_code_needs_three_ascii_letters(name):
    with pytest.raises(AutoCodeUnavailable):
        Company.create(name)


@pytest.mark.parametrize("code", ["", " ", " ABC", "ABC ", "AB", "ABCD", "A1C", "ÄBC", "ABC\n"])
def test_manual_code_rejects_invalid_format(code):
    with pytest.raises(InvalidCompanyValue):
        CompanyCode(code)


def test_name_and_code_value_semantics():
    assert CompanyName("  삼성  전자\n") == CompanyName("삼성  전자")
    assert CompanyCode("aBc") == CompanyCode("ABC")
    assert Company.create("삼성", "abc").code.value == "ABC"
    assert len(CompanyName("가" * 200).value) == 200


@pytest.mark.parametrize("name", ["", " \t\n", "a" * 201, "a\x00b", "ABC\ud800", "ABC\udfff"])
def test_name_boundaries(name):
    with pytest.raises(InvalidCompanyValue):
        CompanyName(name)


def test_identity_immutable_code_and_rename():
    company = Company.create("Samsung")
    same_id = Company(
        company.id, CompanyName("Other"), company.code, company.created_at, company.updated_at
    )
    assert company == same_id
    assert company != Company.create("Samsung")
    assert hash(company) == hash(same_id)
    initial_time = company.updated_at
    assert not company.rename("  Samsung  ")
    assert company.updated_at == initial_time
    assert company.rename("Samsung Electronics")
    assert company.code.value == "SAM"
    for target, attribute, value in [
        (company, "code", CompanyCode("NEW")),
        (company.name, "value", "bypass"),
    ]:
        with pytest.raises(FrozenInstanceError):
            setattr(target, attribute, value)


def test_log_snapshots_are_copied_and_immutable():
    company = Company.create("Samsung")
    snapshot = company.snapshot()
    log = CompanyLog.record(company.id, "create", uuid4(), None, snapshot)
    snapshot["name"] = "changed"
    assert log.after is not None and log.after["name"] == "Samsung"
    with pytest.raises(TypeError):
        operator.setitem(cast(MutableMapping[str, str], log.after), "name", "changed")
    with pytest.raises(ValueError):
        CompanyLog.record(company.id, "delete", uuid4(), None, None)
