#!/usr/bin/env python
# encoding: UTF-8
# Copyright Kapsi Internet-käyttäjät ry
# Idea from http://code.google.com/p/python-iptools ; code completely new

import socket
import struct

def ipv6_to_long(ip):
    ip_bytes_n = socket.inet_pton(socket.AF_INET6, ip)
    ip_parts = struct.unpack('!QQ', ip_bytes_n)
    return 2**64 * ip_parts[0] + ip_parts[1]

def ipv4_to_long(ip):
    ip_bytes_n = socket.inet_pton(socket.AF_INET, ip)
    return struct.unpack('!I', ip_bytes_n)[0]

def long_to_ipv4(ip_long):
    ip_bytes = struct.pack("!I", ip_long)
    return socket.inet_ntop(socket.AF_INET, ip_bytes)

def long_to_ipv6(ip_long):
    ip_parts = (ip_long/2**64, ip_long % 2**64)
    ip_bytes = struct.pack("!QQ", *ip_parts)
    return socket.inet_ntop(socket.AF_INET6, ip_bytes)

def ipv4_mask_to_long(mask):
    mask_binary = ("1" * mask) + ("0" * (32-mask))
    return long(mask_binary, 2)

def ipv6_mask_to_long(mask):
    mask_binary = ("1" * mask) + ("0" * (128-mask))
    return long(mask_binary, 2)

def cidr_to_network(ip, prefixlen):
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
    """IP range list that supports CIDR notation for IPv4 and IPv6"""

    def __init__(self, *args):
        self._masks = []
        for cidr in args:
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

def main():
    ip = "2001:db8:0::1"
    mask = "/24"
    ip_long = ipv6_to_long(ip)
    print ip, "=", ip_long
    ip = long_to_ipv6(ip_long)
    print ip_long, "=", ip
    print "IPv4/24 = " + hex(ipv4_mask_to_long(24))
    print "IPv6/32 = " + hex(ipv6_mask_to_long(32))
    ranges = IpRangeList("10.0.0.0/24", "2001:db8::1/64")
    print ranges._masks
    print "2001:db8:1::1 in ranges:", "2001:db8:1::1" in ranges
    print "2001:db8::1 in ranges:", "2001:db8::1" in ranges
    print "10.0.0.255 in ranges:", "10.0.0.255" in ranges
    print "10.0.1.0 in ranges:", "10.0.1.0" in ranges

if __name__ == '__main__':
    main()