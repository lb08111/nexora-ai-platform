# -*- coding: utf-8 -*-
import pytest

from qwenpaw.discovery.segments.taxonomy import load_segments, lookup_segment


def test_load_segments():
    segs = load_segments()
    assert len(segs) > 0
    assert segs[0].key == "ecommerce"
    assert "loja virtual" in segs[0].keywords


def test_lookup_segment_known():
    result = lookup_segment("tenho uma loja virtual")
    assert result is not None
    assert result.key == "ecommerce"


def test_lookup_segment_known_restaurante():
    result = lookup_segment("sou dono de um restaurante")
    assert result is not None
    assert result.key == "alimentacao"


def test_lookup_segment_unknown():
    result = lookup_segment("mineração de asteroides")
    assert result is None


def test_lookup_segment_case_insensitive():
    result1 = lookup_segment("LOJA VIRTUAL")
    result2 = lookup_segment("loja virtual")
    assert result1 == result2
    assert result1.key == "ecommerce"
