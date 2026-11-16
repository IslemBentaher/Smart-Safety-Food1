# Architecture

Browser (static/ SPA) -> `/api/*` (api.py, Flask blueprint) -> services.py (business logic)
-> nutrition / profile / insights / safety (pure functions, no I/O) and db.py (store).

db.py exposes one interface with two backends: MongoStore (real MongoDB) and
MemoryStore (fallback when MongoDB is unreachable). Env vars: MONGO_URI, MONGO_DB,
STORAGE (auto|memory|mongo).

Docker: one image runs gunicorn (1 worker, 4 threads). docker-compose adds MongoDB.
CI: test -> compose smoke test -> push image to ghcr.io (main only).
