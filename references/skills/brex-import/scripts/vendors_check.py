#!/usr/bin/env python3
"""Check freshness of the Vendors.json disk cache.

Prints FRESH if the file exists and is < 14 days old, otherwise STALE.

Usage:
    python vendors_check.py <vendors_json_path>
"""
import os, sys, time

if len(sys.argv) < 2:
    sys.exit("vendors_check.py: path required -- python vendors_check.py <vendors_json_path>")

path = sys.argv[1]
MAX_AGE = 14 * 24 * 3600  # 14 days in seconds

if os.path.exists(path) and (time.time() - os.path.getmtime(path)) < MAX_AGE:
    print("FRESH")
else:
    print("STALE")
