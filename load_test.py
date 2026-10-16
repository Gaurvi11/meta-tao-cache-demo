"""
Simulates 10 write-then-immediate-read cycles on the same key, through
both a lookaside cache and a write-through (TAO-style) cache.

For lookaside, the realistic order is: write DB -> read (cache not yet
invalidated) -> invalidate. That gap between write and invalidation is
exactly where a stale read can sneak in.
"""

import requests

BASE_URL = "http://localhost:8100"

KEY = "profile:1"
NUM_CYCLES = 10


def run_lookaside():
    print("\n--- LOOKASIDE cache ---")
    # seed: write and read once to populate the cache with an initial value
    requests.post(f"{BASE_URL}/write/lookaside", json={"key": KEY, "value": "v0"})
    requests.post(f"{BASE_URL}/read/lookaside", json={"key": KEY})

    # Note: invalidation is intentionally NOT called here. In a real lookaside
    # setup, invalidation is asynchronous and can lag or get lost -- this
    # models that gap directly instead of assuming it always fires instantly.
    for i in range(1, NUM_CYCLES + 1):
        new_value = f"v{i}"
        requests.post(f"{BASE_URL}/write/lookaside", json={"key": KEY, "value": new_value})
        r = requests.post(f"{BASE_URL}/read/lookaside", json={"key": KEY}).json()
        print(f"  Cycle {i}: wrote {new_value}, read back {r['value']!r} "
              f"({'STALE' if r['stale'] else 'fresh'})")


def run_writethrough():
    print("\n--- WRITE-THROUGH cache (TAO-style) ---")
    for i in range(1, NUM_CYCLES + 1):
        new_value = f"v{i}"
        requests.post(f"{BASE_URL}/write/writethrough", json={"key": KEY, "value": new_value})
        r = requests.post(f"{BASE_URL}/read/writethrough", json={"key": KEY}).json()
        print(f"  Cycle {i}: wrote {new_value}, read back {r['value']!r} "
              f"({'STALE' if r['stale'] else 'fresh'})")


if __name__ == "__main__":
    print("Resetting state...")
    requests.post(f"{BASE_URL}/reset")

    run_lookaside()
    run_writethrough()

    print("\n--- Summary ---")
    status = requests.get(f"{BASE_URL}/status").json()
    print(f"LOOKASIDE:     {status['lookaside']['stale_reads']}/{status['lookaside']['total_reads']} reads were stale")
    print(f"WRITE-THROUGH: {status['writethrough']['stale_reads']}/{status['writethrough']['total_reads']} reads were stale")
