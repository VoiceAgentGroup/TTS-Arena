"""
Utility functions for models.
"""


def anonymize_ip_address(ip_address):
    """
    Remove the last 1-2 octets from an IP address for privacy compliance.
    Examples:
    - 192.168.1.100 -> 192.168.0.0
    - 2001:db8::1 -> 2001:db8::
    """
    if not ip_address:
        return None
    
    try:
        if ':' in ip_address:  # IPv6
            # Keep first 4 groups, zero out the rest
            parts = ip_address.split(':')
            if len(parts) >= 4:
                return ':'.join(parts[:4]) + '::'
            else:
                return ip_address
        else:  # IPv4
            # Keep first 2 octets, zero out last 2
            parts = ip_address.split('.')
            if len(parts) == 4:
                return f"{parts[0]}.{parts[1]}.0.0"
            else:
                return ip_address
    except Exception:
        return None