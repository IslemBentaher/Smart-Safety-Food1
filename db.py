"""Persistence adapters and application store configuration."""
from copy import deepcopy
import os
import threading
import uuid


def _matches(document, query):
    for key, expected in (query or {}).items():
        actual = document.get(key)
        if isinstance(expected, dict):
            for operator, value in expected.items():
                if operator == "$in":
                    if actual not in value:
                        return False
                elif operator == "$gte":
                    if actual is None or actual < value:
                        return False
                elif operator == "$lte":
                    if actual is None or actual > value:
                        return False
                elif operator == "$gt":
                    if actual is None or actual <= value:
                        return False
                elif operator == "$lt":
                    if actual is None or actual >= value:
                        return False
                elif operator == "$ne":
                    if actual == value:
                        return False
                else:
                    raise ValueError("Unsupported query operator: %s" % operator)
        elif actual != expected:
            return False
    return True


def _changes(update):
    if "$set" in update:
        return deepcopy(update["$set"])
    return deepcopy(update)


class MemoryStore:
    """Thread-safe document store used for demos and tests."""

    def __init__(self):
        self._collections = {}
        self._lock = threading.RLock()

    def insert(self, collection, document):
        row = deepcopy(document)
        row.setdefault("id", uuid.uuid4().hex)
        with self._lock:
            self._collections.setdefault(collection, []).append(row)
        return deepcopy(row)

    def find(self, collection, query=None, sort=None, limit=None):
        with self._lock:
            rows = [deepcopy(row) for row in self._collections.get(collection, [])
                    if _matches(row, query)]
        if sort:
            for key, direction in reversed(sort):
                rows.sort(key=lambda row: (row.get(key) is None, row.get(key)),
                          reverse=direction < 0)
        if limit is not None and limit > 0:
            rows = rows[:limit]
        return rows

    def find_one(self, collection, query=None):
        rows = self.find(collection, query, limit=1)
        return rows[0] if rows else None

    def count(self, collection, query=None):
        with self._lock:
            return sum(1 for row in self._collections.get(collection, [])
                       if _matches(row, query))

    def update(self, collection, query, update, upsert=False):
        changes = _changes(update)
        with self._lock:
            rows = self._collections.setdefault(collection, [])
            for row in rows:
                if _matches(row, query):
                    row.update(changes)
                    return True
            if not upsert:
                return False
            row = {key: deepcopy(value) for key, value in (query or {}).items()
                   if not isinstance(value, dict)}
            row.update(changes)
            row.setdefault("id", uuid.uuid4().hex)
            rows.append(row)
            return True

    def delete(self, collection, query=None):
        with self._lock:
            rows = self._collections.get(collection, [])
            kept = [row for row in rows if not _matches(row, query)]
            deleted = len(rows) - len(kept)
            self._collections[collection] = kept
            return deleted

    def clear(self):
        with self._lock:
            self._collections.clear()


class MongoStore:
    """MongoDB-backed implementation of the same small document-store API."""

    def __init__(self, database):
        self.database = database

    def insert(self, collection, document):
        row = deepcopy(document)
        row.setdefault("id", uuid.uuid4().hex)
        self.database[collection].insert_one(row)
        return row

    def find(self, collection, query=None, sort=None, limit=None):
        cursor = self.database[collection].find(query or {})
        if sort:
            cursor = cursor.sort(sort)
        if limit is not None and limit > 0:
            cursor = cursor.limit(limit)
        rows = []
        for document in cursor:
            document.pop("_id", None)
            rows.append(document)
        return rows

    def find_one(self, collection, query=None):
        document = self.database[collection].find_one(query or {})
        if document is None:
            return None
        document.pop("_id", None)
        return document

    def count(self, collection, query=None):
        return self.database[collection].count_documents(query or {})

    def update(self, collection, query, update, upsert=False):
        result = self.database[collection].update_one(
            query or {}, {"$set": _changes(update)}, upsert=upsert)
        return bool(result.matched_count or result.upserted_id)

    def delete(self, collection, query=None):
        return self.database[collection].delete_many(query or {}).deleted_count

    def clear(self):
        for name in self.database.list_collection_names():
            self.database[name].delete_many({})


def _make_store():
    if os.environ.get("STORAGE", "").strip().lower() == "memory":
        return MemoryStore(), "memory"
    try:
        from pymongo import MongoClient
        from pymongo.errors import PyMongoError

        uri = os.environ.get("MONGODB_URI", "mongodb://127.0.0.1:27017")
        name = os.environ.get("MONGODB_DATABASE", "smart_health_food")
        client = MongoClient(uri, serverSelectionTimeoutMS=500)
        client.admin.command("ping")
        return MongoStore(client[name]), "mongodb"
    except (ImportError, OSError):
        return MemoryStore(), "memory"
    except Exception as exc:
        # A missing/unavailable Mongo service is an expected local-development case.
        try:
            from pymongo.errors import PyMongoError
        except ImportError:
            return MemoryStore(), "memory"
        if isinstance(exc, PyMongoError):
            return MemoryStore(), "memory"
        raise


_store, _storage_name = _make_store()


def get_store():
    return _store


def storage_name():
    return _storage_name


def reset():
    """Clear application data and restore the immutable built-in food catalog."""
    _store.clear()
    from foods import BUILTIN_FOODS

    for food in BUILTIN_FOODS:
        _store.insert("foods", food)
