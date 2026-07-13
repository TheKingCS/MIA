"""
core.subnet_calculator
=========================

Subnet/CIDR calculator — docs/ROADMAP.md milestone 11.5, Field Kit's
Security/Network Toolkit. A thin wrapper around stdlib `ipaddress`
(handles both IPv4 and IPv6 correctly) rather than hand-rolling bitmask
math — "don't reinvent the wheel", same reasoning behind this
project's other integration decisions (Kiwix for reference content,
`astral` for sun/moon).
"""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from typing import Optional


@dataclass
class SubnetInfo:
    network_address: str
    broadcast_address: str
    netmask: str
    prefix_length: int
    total_addresses: int
    usable_host_count: int
    first_usable: Optional[str]
    last_usable: Optional[str]


def calculate_subnet(cidr: str) -> SubnetInfo:
    """
    Raises ValueError (via `ipaddress.ip_network`) for invalid input —
    left to the caller to catch and display, same as every other
    "parse user input, let the caller surface a validation error"
    boundary in this app. `strict=False` allows host bits set in the
    input (e.g. "192.168.1.5/24") rather than requiring an exact
    network address, matching how most real-world subnet calculators
    behave.

    Deliberately never calls `network.hosts()`/materializes a host
    list: for a large or IPv6 network (e.g. a /64 has ~1.8*10^19
    addresses), iterating or listing every host address is not just
    slow but genuinely unbounded memory growth — confirmed the hard way
    when a test exercising "2001:db8::/64" ballooned a test run to
    several GB and had to be killed. `usable_host_count`/`first_usable`/
    `last_usable` are instead derived by O(1) arithmetic on
    `num_addresses`/`network_address`/`broadcast_address`, which is
    correct and cheap regardless of network size.
    """
    network = ipaddress.ip_network(cidr, strict=False)
    total_addresses = network.num_addresses

    # A /31 or /32 (IPv4) or /127 or /128 (IPv6) has no usable host
    # range in the traditional sense (RFC 3021's /31 point-to-point
    # special case is a real exception a field subnet calculator
    # doesn't need to special-case here).
    if total_addresses <= 2:
        usable_host_count = 0
        first_usable = None
        last_usable = None
    else:
        usable_host_count = total_addresses - 2
        first_usable = str(network.network_address + 1)
        last_usable = str(network.broadcast_address - 1)

    return SubnetInfo(
        network_address=str(network.network_address),
        broadcast_address=str(network.broadcast_address),
        netmask=str(network.netmask),
        prefix_length=network.prefixlen,
        total_addresses=total_addresses,
        usable_host_count=usable_host_count,
        first_usable=first_usable,
        last_usable=last_usable,
    )
