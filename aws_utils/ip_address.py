import requests
import ipaddress


class AWSIPAddress:
    """Class to help understand if an IP address belongs to AWS or not"""

    @classmethod
    def get_aws_ranges(cls):
        if not hasattr(cls, "_aws_ranges"):
            response = requests.get("https://ip-ranges.amazonaws.com/ip-ranges.json")
            if response.status_code != 200:
                raise Exception(f"Error getting ip-ranges.json: {response.status_code}")
            cls._aws_ranges = response.json()
        return cls._aws_ranges

    @classmethod
    def get_region_from_ip(cls, ip_address):
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
