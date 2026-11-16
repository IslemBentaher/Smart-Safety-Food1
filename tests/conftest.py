"""pytest setup: use the in-memory store so tests never touch a real MongoDB."""
import os

os.environ["STORAGE"] = "memory"  # must be set before db.py is used

import pytest

import db


@pytest.fixture(autouse=True)
def fresh_store():
    db.reset()  # every test starts with an empty store (foods are re-seeded)
    yield
    db.reset()


@pytest.fixture
def client():
    from app import app

    return app.test_client()
