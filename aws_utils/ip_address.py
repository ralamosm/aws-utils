import ipaddress
import socket
from typing import Any
from typing import Dict
from typing import Optional
from urllib.parse import urlparse

import requests
import validators


class AWSIPAddress:
    """Class to help understand if an IP address belongs to AWS or not"""

    @classmethod
    def get_aws_ranges(cls) -> Dict:
        if not hasattr(cls, "_aws_ranges"):
            response = requests.get("https://ip-ranges.amazonaws.com/ip-ranges.json")
            if response.status_code != 200:
                raise Exception(f"Error getting ip-ranges.json: {response.status_code}")
            cls._aws_ranges = response.json()
        return cls._aws_ranges

    @classmethod
    def get_region_from_ip(cls, ip_address: str) -> str:
        data = cls.get_aws_ranges()
        ip = ipaddress.ip_address(ip_address)
        for prefix in data["prefixes"]:
            network = ipaddress.ip_network(prefix["ip_prefix"])
            if ip in network:
                return prefix["region"]

        for prefix in data["ipv6_prefixes"]:
            network = ipaddress.ip_network(prefix["ipv6_prefix"])
            if ip in network:
                return prefix["region"]

        raise ValueError(f"Region not found for IP address: `{ip_address}`")


def get_ip_address(hostname: str) -> Any:
    try:
        ip_address = socket.gethostbyname(hostname)
        return ip_address
    except socket.error:
        return None


def is_aws(target: str, include_global: Optional[bool] = True) -> bool:
    """Helper to quickly check if a given input belongs to AWS"""
    while not validators.ipv4(target) and not validators.ipv6(target):
        if validators.url(target):
            p = urlparse(target)
            if not p.netloc:
                return False

            netloc = p.netloc if ":" not in p.netloc else p.netloc.split(":")[0]
            target = get_ip_address(netloc)
        elif validators.domain(target):
            target = get_ip_address(target)
        elif validators.ipv4(target) or validators.ipv6(target):
            break
        else:
            return False

    if target is None:
        return False

    target = target.lower()
    ip = ipaddress.ip_address(target)
    if ip.is_private:
        return False

    try:
        region = AWSIPAddress.get_region_from_ip(target)
        if region.lower() == "global" and include_global:
            # this is route 53, cloudfront, etc. Ignore.
            return True
    except Exception as e:
        # no AWS, no problemo, but no record also
        if "region not found for ip address" in str(e).lower():
            return False
        raise

    return True
