import operator
from collections.abc import MutableMapping
from dataclasses import FrozenInstanceError
from typing import cast
from unicodedata import normalize
from uuid import uuid4

import pytest

from mdm_demo.domain.entities.network import Network
from mdm_demo.domain.entities.network_log import NetworkLog
from mdm_demo.domain.errors.network import InvalidNetworkValue
from mdm_demo.domain.value_objects.network_code import NetworkCode
from mdm_demo.domain.value_objects.network_name import NetworkName


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
    assert NetworkName(raw).value == expected
    assert NetworkName(raw) == NetworkName(expected)


@pytest.mark.parametrize("raw", ["", " \t\n", "a" * 101, "ß" * 51, "a\x00b", "\ud800", "\udfff"])
def test_invalid_name(raw):
    with pytest.raises(InvalidNetworkValue):
        NetworkName(raw)


@pytest.mark.parametrize("raw", ["", " ", "A" * 21, "ＫＯＲ", "KOR", "K R", "ÄBC", "LTE-A"])
def test_invalid_code(raw):
    with pytest.raises(InvalidNetworkValue):
        NetworkCode(raw)


def test_entity_identity_immutable_code_and_normalized_noop():
    network = Network.create(" korea ", " kor ")
    assert network.code == NetworkCode("KOR")
    same = Network(
        network.id, NetworkName("OTHER"), network.code, network.created_at, network.updated_at
    )
    assert same == network and hash(same) == hash(network)
    assert network != Network.create("KOREA", "KOR")
    before = network.updated_at
    assert not network.rename(" korea ")
    assert network.updated_at == before
    assert network.rename("대한민국")
    assert not network.rename(normalize("NFD", "대한민국"))
    assert network.code.value == "KOR"
    for attribute in ("code", "name"):
        with pytest.raises(FrozenInstanceError):
            setattr(network, attribute, NetworkCode("NEW"))


def test_log_snapshot_copy_and_immutability():
    network = Network.create("Korea", "KOR")
    snapshot = network.snapshot()
    log = NetworkLog.record(network.id, "create", uuid4(), None, snapshot)
    snapshot["name"] = "CHANGED"
    assert log.after is not None and log.after["name"] == "KOREA"
    with pytest.raises(TypeError):
        operator.setitem(cast(MutableMapping[str, str], log.after), "name", "CHANGED")
    with pytest.raises(ValueError):
        NetworkLog.record(network.id, "delete", uuid4(), None, None)


@pytest.mark.parametrize(
    ("raw", "expected"), [("3g", "3G"), (" 5g ", "5G"), ("A", "A"), ("a" * 20, "A" * 20)]
)
def test_manual_code_boundaries(raw, expected):
    assert NetworkCode(raw).value == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("3G", "3G"),
        ("5G NR", "5GNR"),
        ("LTE-A", "LTEA"),
        ("이동통신 5g", "5G"),
        ("B" * 20, "B" * 20),
    ],
)
def test_auto_code_extracts_all_normalized_ascii(raw, expected):
    assert Network.create(raw).code.value == expected


@pytest.mark.parametrize("raw", ["이동통신", "---", "C" * 21])
def test_auto_code_does_not_truncate_or_invent(raw):
    from mdm_demo.domain.errors import AutoCodeUnavailable

    with pytest.raises(AutoCodeUnavailable):
        Network.create(raw)
    assert Network.create(raw, "CUSTOM").code.value == "CUSTOM"
