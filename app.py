"""
Meta TAO write-through cache demo (illustrative, local-only simulation).

Simulates the exact race condition TAO was built to avoid: in a lookaside
cache, a write updates the database first, and the cache invalidation
arrives separately, slightly later. Any read that lands in that gap gets
a stale value AND re-caches it, extending the staleness.

A write-through cache (TAO's model) updates the cache as PART of the
write itself, so there's no gap for a stale read to sneak into.

  /write/lookaside + /read/lookaside + /invalidate/lookaside
      -> models the three separate steps of a lookaside cache, in the
         realistic order: write DB, (read can happen here), invalidate.

  /write/writethrough + /read/writethrough
      -> write updates the DB and the cache together, atomically. A read
         right after a write always sees the fresh value.

GET /status returns stale-read counts for both strategies.
POST /reset restores everything to a clean baseline.
"""

from flask import Flask, request, jsonify

app = Flask(__name__)

lookaside_db = {}
lookaside_cache = {}
lookaside_stale_reads = 0
lookaside_total_reads = 0

writethrough_db = {}
writethrough_cache = {}
writethrough_stale_reads = 0
writethrough_total_reads = 0


@app.route("/write/lookaside", methods=["POST"])
def write_lookaside():
    data = request.get_json()
    key, value = data["key"], data["value"]
    lookaside_db[key] = value
    # cache is NOT touched here -- invalidation arrives separately, later
    return jsonify({"mode": "lookaside", "status": "db_updated", "cache_still_stale": key in lookaside_cache})


@app.route("/read/lookaside", methods=["POST"])
def read_lookaside():
    global lookaside_stale_reads, lookaside_total_reads
    data = request.get_json()
    key = data["key"]
    lookaside_total_reads += 1

    if key in lookaside_cache:
        value = lookaside_cache[key]
        is_stale = value != lookaside_db.get(key)
        if is_stale:
            lookaside_stale_reads += 1
        return jsonify({"mode": "lookaside", "value": value, "stale": is_stale})

    # cache miss: fetch fresh from DB and cache it
    value = lookaside_db.get(key)
    lookaside_cache[key] = value
    return jsonify({"mode": "lookaside", "value": value, "stale": False})


@app.route("/invalidate/lookaside", methods=["POST"])
def invalidate_lookaside():
    data = request.get_json()
    key = data["key"]
    lookaside_cache.pop(key, None)
    return jsonify({"mode": "lookaside", "status": "invalidated"})


@app.route("/write/writethrough", methods=["POST"])
def write_writethrough():
    data = request.get_json()
    key, value = data["key"], data["value"]
    writethrough_db[key] = value
    writethrough_cache[key] = value  # updated atomically, as part of the write
    return jsonify({"mode": "writethrough", "status": "db_and_cache_updated"})


@app.route("/read/writethrough", methods=["POST"])
def read_writethrough():
    global writethrough_stale_reads, writethrough_total_reads
    data = request.get_json()
    key = data["key"]
    writethrough_total_reads += 1

    value = writethrough_cache.get(key)
    is_stale = value != writethrough_db.get(key)
    if is_stale:
        writethrough_stale_reads += 1
    return jsonify({"mode": "writethrough", "value": value, "stale": is_stale})


@app.route("/status", methods=["GET"])
def status():
    return jsonify({
        "lookaside": {
            "total_reads": lookaside_total_reads,
            "stale_reads": lookaside_stale_reads,
        },
        "writethrough": {
            "total_reads": writethrough_total_reads,
            "stale_reads": writethrough_stale_reads,
        },
    })


@app.route("/reset", methods=["POST"])
def reset():
    global lookaside_db, lookaside_cache, lookaside_stale_reads, lookaside_total_reads
    global writethrough_db, writethrough_cache, writethrough_stale_reads, writethrough_total_reads
    lookaside_db = {}
    lookaside_cache = {}
    lookaside_stale_reads = 0
    lookaside_total_reads = 0
    writethrough_db = {}
    writethrough_cache = {}
    writethrough_stale_reads = 0
    writethrough_total_reads = 0
    return jsonify({"status": "reset"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8100, debug=True)
