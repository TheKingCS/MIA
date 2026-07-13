"""
tests.test_subnet_calculator
===============================

Unit tests for core.subnet_calculator — real stdlib `ipaddress` calls,
not mocked (there's nothing external to fake; this is pure computation
against known-correct real values).
"""

from __future__ import annotations

import pytest

from core.subnet_calculator import calculate_subnet


def test_standard_slash_24():
    info = calculate_subnet("192.168.1.0/24")
    assert info.network_address == "192.168.1.0"
    assert info.broadcast_address == "192.168.1.255"
    assert info.netmask == "255.255.255.0"
    assert info.prefix_length == 24
    assert info.total_addresses == 256
    assert info.usable_host_count == 254
    assert info.first_usable == "192.168.1.1"
    assert info.last_usable == "192.168.1.254"


def test_slash_30_small_subnet():
    info = calculate_subnet("10.0.0.0/30")
    assert info.total_addresses == 4
    assert info.usable_host_count == 2
    assert info.first_usable == "10.0.0.1"
    assert info.last_usable == "10.0.0.2"


def test_slash_32_single_host_has_no_usable_range():
    info = calculate_subnet("10.0.0.5/32")
    assert info.total_addresses == 1
    assert info.usable_host_count == 0
    assert info.first_usable is None
    assert info.last_usable is None


def test_non_strict_accepts_host_bits_set():
    """192.168.1.5/24 has host bits set — strict=False should still resolve the containing network."""
    info = calculate_subnet("192.168.1.5/24")
    assert info.network_address == "192.168.1.0"


def test_slash_16():
    info = calculate_subnet("172.16.0.0/16")
    assert info.total_addresses == 65536
    assert info.usable_host_count == 65534


def test_ipv6_network():
    info = calculate_subnet("2001:db8::/64")
    assert info.network_address == "2001:db8::"
    assert info.prefix_length == 64


def test_invalid_cidr_raises_value_error():
    with pytest.raises(ValueError):
        calculate_subnet("not-an-ip/24")


def test_invalid_prefix_raises_value_error():
    with pytest.raises(ValueError):
        calculate_subnet("192.168.1.0/99")
