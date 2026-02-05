#!/usr/bin/env python3
"""
Force IPv4 connection for PostgreSQL in WSL environments.
Run this before starting the backend server.
"""

import socket
import os

# Monkey patch socket.getaddrinfo to prefer IPv4
_original_getaddrinfo = socket.getaddrinfo

def getaddrinfo_ipv4_only(host, port, family=0, type=0, proto=0, flags=0):
    """Force IPv4 (AF_INET) resolution"""
    return _original_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)

# Apply the patch
socket.getaddrinfo = getaddrinfo_ipv4_only

print("✓ IPv4-only mode enabled for database connections")
print("  This forces PostgreSQL to use IPv4 addresses")
print("")

if __name__ == "__main__":
    # Test the connection
    from db.pg_connections import engine
    print("Testing database connection...")
    with engine.connect() as conn:
        print("✓ Successfully connected to PostgreSQL via IPv4!")
