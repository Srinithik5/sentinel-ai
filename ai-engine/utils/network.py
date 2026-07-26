from __future__ import annotations

import hashlib
import ipaddress
import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Office:
    name: str
    city: str
    country: str
    timezone: str
    network_cidr: str


OFFICES: tuple[Office, ...] = (
    Office("New York HQ", "New York", "USA", "America/New_York", "10.10.0.0/16"),
    Office("London Office", "London", "United Kingdom", "Europe/London", "10.20.0.0/16"),
    Office("Bangalore Office", "Bangalore", "India", "Asia/Kolkata", "10.30.0.0/16"),
    Office("Singapore Office", "Singapore", "Singapore", "Asia/Singapore", "10.40.0.0/16"),
    Office("Berlin Office", "Berlin", "Germany", "Europe/Berlin", "10.50.0.0/16"),
    Office("Sydney Office", "Sydney", "Australia", "Australia/Sydney", "10.60.0.0/16"),
)

# RFC 6598 carrier-grade NAT range — used as a safe stand-in for remote/residential
# egress IPs so no output could resemble a real organization's public IP space.
REMOTE_NETWORK_CIDR = "100.64.0.0/10"


def random_ip_in_cidr(cidr: str, rng: random.Random) -> str:
    network = ipaddress.ip_network(cidr)
    host_bits = network.max_prefixlen - network.prefixlen
    max_offset = max(1, (2**host_bits) - 2)
    offset = rng.randint(1, max_offset)
    return str(ipaddress.ip_address(int(network.network_address) + offset))


def stable_ip_for_entity(entity_id: str, cidr: str) -> str:
    network = ipaddress.ip_network(cidr)
    host_bits = network.max_prefixlen - network.prefixlen
    max_offset = max(1, (2**host_bits) - 2)
    seed = int(hashlib.sha256(entity_id.encode()).hexdigest(), 16)
    offset = (seed % max_offset) + 1
    return str(ipaddress.ip_address(int(network.network_address) + offset))
def generate_device_fingerprint(seed_value: str) -> str:
    return hashlib.sha256(seed_value.encode()).hexdigest()[:32]