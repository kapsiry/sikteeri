#!/usr/bin/env python
# encoding: UTF-8
# Copyright Kapsi Internet-käyttäjät ry
# Idea from http://code.google.com/p/python-iptools ; code completely new

import socket
import struct

def ipv6_to_long(ip):
    """Return the IPv6 address string as a long

    >>> ipv6_to_long("2001:db8::1")
    42540766411282592856903984951653826561L
    >>> ipv6_to_long("::1")
    1L
    """
    ip_bytes_n = socket.inet_pton(socket.AF_INET6, ip)
    ip_parts = struct.unpack('!QQ', ip_bytes_n)
    return 2**64 * ip_parts[0] + ip_parts[1]

def ipv4_to_long(ip):
    """Return the IPv4 address string as a long

    >>> ipv4_to_long("127.0.0.1")
    2130706433L
    >>> ipv4_to_long("1.2.3.4")
    16909060L
    """
    ip_bytes_n = socket.inet_pton(socket.AF_INET, ip)
    return long(struct.unpack('!I', ip_bytes_n)[0])

def long_to_ipv4(ip_long):
    """Convert a long representation to a human readable IPv4 string

    >>> long_to_ipv4(2130706433L)
    '127.0.0.1'
    >>> long_to_ipv4(16909060L)
    '1.2.3.4'
    """
    ip_bytes = struct.pack("!I", ip_long)
    return socket.inet_ntop(socket.AF_INET, ip_bytes)

def long_to_ipv6(ip_long):
    """Convert a long representation to a human readable IPv6 string

    >>> long_to_ipv6(42540766411282592856903984951653826561L)
    '2001:db8::1'
    >>> long_to_ipv6(1L)
    '::1'
    """
    ip_parts = (ip_long/2**64, ip_long % 2**64)
    ip_bytes = struct.pack("!QQ", *ip_parts)
    return socket.inet_ntop(socket.AF_INET6, ip_bytes)

def ipv4_mask_to_long(mask):
    """Convert an IPv4 netmax (prefixlen) to long

    >>> ipv4_mask_to_long(24)
    4294967040L
    >>> ipv4_mask_to_long(8)
    4278190080L
    """
    mask_binary = ("1" * mask) + ("0" * (32-mask))
    return long(mask_binary, 2)

def ipv6_mask_to_long(mask):
    """Convert an IPv6 prefixlen to long

    >>> ipv6_mask_to_long(64)
    340282366920938463444927863358058659840L
    >>> ipv6_mask_to_long(128)
    340282366920938463463374607431768211455L
    """
    mask_binary = ("1" * mask) + ("0" * (128-mask))
    return long(mask_binary, 2)

def cidr_to_network(ip, prefixlen):
    """Calculate the network address for a CIDR notation network

    >>> cidr_to_network("127.1.1.1", 8)
    '127.0.0.0'
    >>> cidr_to_network("172.16.32.6", 24)
    '172.16.32.0'
    """
    if ':' in ip: # IPv6
        netmask = ipv6_mask_to_long(prefixlen)
        ip_long = ipv6_to_long(ip)
        network_long = ip_long & netmask
        network = long_to_ipv6(network_long)
    else:
        netmask = ipv4_mask_to_long(prefixlen)
        ip_long = ipv4_to_long(ip)
        network_long = ip_long & netmask
        network = long_to_ipv4(network_long)
    return network

class IpRangeList:
    """IP range list that supports CIDR notation for IPv4 and IPv6

    >>> r = IpRangeList("10.0.0.1", "172.16.4.254/24", "2001:db8::1/64")
    >>> "10.0.0.1" in r
    True
    >>> "10.0.0.2" in r
    False
    >>> "172.16.4.0" in r
    True
    >>> "172.16.4.255" in r
    True
    >>> "172.16.5.0" in r
    False
    >>> "2001:db8::ffff:ffff:ffff:ffff" in r
    True
    >>> "2001:db8:1::1" in r
    False
    >>> "2001:db8::" in r
    True
    """

    def __init__(self, *args):
        self._masks = []
        for cidr in args:
            if not '/' in cidr:
                ip = cidr
                if ':' in ip:
                    prefixlen = 128
                else:
                    prefixlen = 32
            else:
                (ip, prefixlen) = cidr.split("/")
            prefixlen = int(prefixlen)
            network = cidr_to_network(ip, prefixlen)
            self._masks.append((network, prefixlen))
    def __contains__(self, x):
        for (network, prefixlen) in self._masks:
            x_network = None
            if ':' in x and ':' in network:
                x_network = cidr_to_network(x, prefixlen)
            elif not ':' in network and not ':' in x:
                x_network = cidr_to_network(x, prefixlen)
            if x_network == network:
                return True
        return False

def load_tests(loader, tests, pattern):
    import doctest
    suite = doctest.DocTestSuite()
    tests.addTests(suite)
    return suite

def main():
    import unittest
    import doctest
    suite = doctest.DocTestSuite()
    unittest.TextTestRunner().run(suite)

if __name__ == '__main__':
    main()
