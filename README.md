# Meta TAO — Write-Through Cache Demo

Companion code for **Day 90/91 | The Incident: Meta**

This is a local, illustrative simulation of the core design decision
behind Meta's TAO: updating the cache as PART of a write, instead of
writing to the database and relying on a separate, asynchronous
invalidation step to keep the cache in sync.

## The idea

In a lookaside cache, a write updates the database, and the cache is
expected to be invalidated separately -- a step that's asynchronous in
real systems, and can lag or get lost. Until that invalidation lands, the
cache keeps serving whatever was cached before.

In a write-through cache (TAO's model), the cache is updated as part of
the write itself, so there's no window in which the cache and database
can disagree.

| Lookaside cache                                 | Write-through cache (TAO-style)                  |
|-----------------------------------------------------|--------------------------------------------------------|
| Write updates the DB; cache is invalidated separately | Write updates the cache and DB together, atomically       |
| A lagging or lost invalidation leaves stale data cached | No gap exists for stale data to be served                 |
| 10/11 reads stale in this demo's run                   | 0/10 reads stale                                          |

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
python3 -m pip install flask requests
```

## Run it

**Terminal 1 — start the app:**
```bash
python3 app.py
```

**Terminal 2 — run the simulated write/read cycles:**
```bash
python3 load_test.py
```

You'll see the same sequence of writes and reads run through both caching
strategies, and the resulting difference in staleness.

## Try it live

```bash
curl -X POST http://localhost:8100/write/writethrough \
  -H "Content-Type: application/json" \
  -d '{"key": "profile:1", "value": "v1"}'

curl -X POST http://localhost:8100/read/writethrough \
  -H "Content-Type: application/json" \
  -d '{"key": "profile:1"}'
```
