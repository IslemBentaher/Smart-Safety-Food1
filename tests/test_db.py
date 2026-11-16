"""The same tests run against the memory store and against MongoStore (using mongomock)."""
import mongomock
import pytest

from db import MemoryStore, MongoStore


@pytest.fixture(params=["memory", "mongo"])
def store(request):
    if request.param == "memory":
        return MemoryStore()
    return MongoStore(mongomock.MongoClient()["test"])


def test_insert_gives_an_id_and_find_returns_copies(store):
    doc = store.insert("c", {"name": "a"})
    assert doc["id"]
    rows = store.find("c")
    assert rows == [{"name": "a", "id": doc["id"]}] and "_id" not in rows[0]
    rows[0]["name"] = "changed"
    assert store.find("c")[0]["name"] == "a"


def test_filters(store):
    for day, n in (("2026-11-01", 1), ("2026-11-02", 2), ("2026-11-03", 3), ("2026-11-04", 4)):
        store.insert("c", {"date": day, "n": n})
    assert [d["n"] for d in store.find("c", {"date": "2026-11-02"})] == [2]
    assert [d["n"] for d in store.find("c", {"date": {"$gte": "2026-11-02", "$lte": "2026-11-03"}})] == [2, 3]
    assert sorted(d["n"] for d in store.find("c", {"n": {"$in": [1, 4]}})) == [1, 4]
    assert store.count("c") == 4 and store.count("c", {"n": 9}) == 0


def test_sort_and_limit(store):
    for n in (3, 1, 2):
        store.insert("c", {"n": n})
    assert [d["n"] for d in store.find("c", sort=[("n", 1)])] == [1, 2, 3]
    assert [d["n"] for d in store.find("c", sort=[("n", -1)], limit=2)] == [3, 2]


def test_find_one(store):
    store.insert("c", {"k": "x", "v": 1})
    assert store.find_one("c", {"k": "x"})["v"] == 1
    assert store.find_one("c", {"k": "missing"}) is None


def test_update_and_upsert(store):
    assert store.update("c", {"k": "x"}, {"v": 1}) is False
    assert store.update("c", {"k": "x"}, {"v": 1}, upsert=True) is True
    created = store.find_one("c", {"k": "x"})
    assert created["v"] == 1 and created["id"]
    assert store.update("c", {"k": "x"}, {"v": 2}, upsert=True) is True
    assert store.count("c") == 1 and store.find_one("c", {"k": "x"})["v"] == 2


def test_delete(store):
    for n in (1, 2, 3):
        store.insert("c", {"n": n})
    assert store.delete("c", {"n": 2}) == 1
    assert store.delete("c", {}) == 2
    assert store.count("c") == 0


def test_seed_foods_is_repeatable(store):
    from db import seed_foods
    from foods import BUILTIN_FOODS

    seed_foods(store)
    seed_foods(store)  # running twice must not create duplicates
    assert store.count("foods") == len(BUILTIN_FOODS)
    assert store.find_one("foods", {"id": "apple"})["name"] == "Apple"
