import pytest

TODAY = "2026-11-10"


def post(client, url, **body):
    return client.post(url, json=body)


def log(client, food_id, grams, meal="lunch", day=TODAY):
    return post(client, "/api/logs", date=day, meal=meal, food_id=food_id, grams=grams)


# ---- basics ----------------------------------------------------------------
def test_home_health_and_404(client):
    assert client.get("/").status_code == 200
    assert client.get("/health").get_json() == {"status": "ok", "storage": "memory"}
    r = client.get("/api/nope")
    assert r.status_code == 404 and "error" in r.get_json()


# ---- foods -----------------------------------------------------------------
def test_food_list_filters_and_sorting(client):
    data = client.get("/api/foods").get_json()
    assert data["total"] >= 70 and "fruit" in data["categories"]
    assert all("health_score" in f and "grade" in f for f in data["foods"])
    assert [f["name"] for f in client.get("/api/foods?q=choc").get_json()["foods"]] == [
        "Dark chocolate (70%)", "Milk chocolate"]
    assert {f["category"] for f in client.get("/api/foods?category=fruit").get_json()["foods"]} == {"fruit"}
    assert {f["grade"] for f in client.get("/api/foods?grade=a").get_json()["foods"]} == {"A"}
    local = client.get("/api/foods?local=1").get_json()["foods"]
    assert local and all(f["local"] for f in local)
    by_score = [f["health_score"] for f in client.get("/api/foods?sort=score").get_json()["foods"]]
    assert by_score == sorted(by_score, reverse=True)
    by_kcal = [f["kcal"] for f in client.get("/api/foods?sort=kcal&order=desc&limit=5").get_json()["foods"]]
    assert len(by_kcal) == 5 and by_kcal == sorted(by_kcal, reverse=True)


def test_food_detail(client):
    data = client.get("/api/foods/milk-chocolate").get_json()
    assert data["food"]["grade"] == "E" and data["score"]["negative"]["sugar"] > 5
    assert data["swaps"] and data["explain"]["bad"]
    assert client.get("/api/foods/unknown").status_code == 404


def test_custom_food_lifecycle(client):
    r = post(client, "/api/foods", name="My bar", category="snack", kcal=400, carbs=50, sugar=20, fat=15, sat_fat=5)
    assert r.status_code == 201
    food = r.get_json()
    assert food["builtin"] is False and food["grade"] in "ABCDE"
    assert any(f["id"] == food["id"] for f in client.get("/api/foods").get_json()["foods"])
    assert client.delete("/api/foods/" + food["id"]).status_code == 200
    assert client.delete("/api/foods/apple").status_code == 400  # built-in
    assert client.delete("/api/foods/" + food["id"]).status_code == 404


@pytest.mark.parametrize("bad", [
    {"name": "", "category": "snack", "kcal": 1},
    {"name": "x", "category": "moon", "kcal": 1},
    {"name": "x", "category": "snack", "kcal": -5},
    {"name": "x", "category": "snack", "kcal": "abc"},
    {"name": "x", "category": "snack", "kcal": 100, "carbs": 10, "sugar": 20},
])
def test_custom_food_validation(client, bad):
    assert post(client, "/api/foods", **bad).status_code == 400


# ---- analyzer --------------------------------------------------------------
def test_analyze(client):
    r = post(client, "/api/analyze", items=[{"food_id": "couscous-meat-veg", "grams": 350},
                                            {"food_id": "milk-chocolate", "grams": 50}])
    data = r.get_json()
    assert r.status_code == 200 and data["score"]["grade"] in "ABCDE"
    assert data["swaps_for"] == "Milk chocolate" and data["swaps"]
    assert round(sum(data["macro_split"].values())) == 100
    assert len(data["items"]) == 2


@pytest.mark.parametrize("body", [
    {}, {"items": []}, {"items": [{"food_id": "nope", "grams": 100}]},
    {"items": [{"food_id": "apple", "grams": 0}]}, {"items": ["apple"]},
    {"items": [{"food_id": "apple", "grams": 100}] * 31},
])
def test_analyze_validation(client, body):
    assert post(client, "/api/analyze", **body).status_code == 400


# ---- profile and weight ----------------------------------------------------
PROFILE = {"name": "Sam", "age": 21, "sex": "male", "height_cm": 175, "weight_kg": 72,
           "activity": "light", "goal": "lose"}


def test_profile(client):
    first = client.get("/api/profile").get_json()
    assert first["is_default"] is True and first["targets"]["kcal"] > 1000
    saved = client.put("/api/profile", json=PROFILE).get_json()
    assert saved["is_default"] is False and saved["profile"]["name"] == "Sam"
    assert saved["metrics"]["bmi"] == 23.5 and saved["metrics"]["tdee"] > saved["targets"]["kcal"]
    assert client.get("/api/profile").get_json()["profile"]["goal"] == "lose"
    assert client.put("/api/profile", json=dict(PROFILE, age=3)).status_code == 400
    assert client.put("/api/profile", json={}).status_code == 400


def test_weight_updates_the_profile(client):
    client.put("/api/profile", json=PROFILE)
    post(client, "/api/weight", date="2026-11-01", weight_kg=73)
    r = post(client, "/api/weight", date="2026-11-08", weight_kg=71.4)
    assert [w["kg"] for w in r.get_json()] == [73, 71.4]
    assert client.get("/api/profile").get_json()["profile"]["weight_kg"] == 71.4
    post(client, "/api/weight", date="2026-11-08", weight_kg=71.0)  # same day: replaced
    assert len(client.get("/api/weight").get_json()) == 2
    assert post(client, "/api/weight", date="2026-11-09", weight_kg=5).status_code == 400


# ---- log and water ---------------------------------------------------------
def test_log_lifecycle(client):
    r = log(client, "apple", 180, "snack")
    entry = r.get_json()
    assert r.status_code == 201 and entry["food_name"] == "Apple" and entry["nutrients"]["kcal"] == 93.6
    assert entry["grade"] == "A"
    assert [e["id"] for e in client.get("/api/logs?date=" + TODAY).get_json()] == [entry["id"]]
    assert client.get("/api/logs?date=2026-11-09").get_json() == []
    assert client.delete("/api/logs/" + entry["id"]).status_code == 200
    assert client.delete("/api/logs/" + entry["id"]).status_code == 404


@pytest.mark.parametrize("body", [
    {"meal": "brunch", "food_id": "apple", "grams": 100},
    {"meal": "lunch", "food_id": "nope", "grams": 100},
    {"meal": "lunch", "food_id": "apple", "grams": 0},
    {"meal": "lunch", "food_id": "apple", "grams": 99999},
    {"meal": "lunch", "food_id": "apple", "grams": 100, "date": "yesterday"},
])
def test_log_validation(client, body):
    assert post(client, "/api/logs", **body).status_code == 400


def test_water(client):
    assert client.get("/api/water?date=" + TODAY).get_json()["ml"] == 0
    assert post(client, "/api/water", date=TODAY, ml=500).get_json()["ml"] == 500
    assert post(client, "/api/water", date=TODAY, ml=250).get_json()["ml"] == 750
    assert post(client, "/api/water", date=TODAY, ml=-2000).get_json()["ml"] == 0  # never below zero
    assert post(client, "/api/water", date=TODAY, ml=99999).status_code == 400


# ---- dashboard -------------------------------------------------------------
def test_dashboard_for_an_empty_day(client):
    d = client.get("/api/dashboard?date=" + TODAY).get_json()
    assert d["is_default"] is True and d["totals"]["kcal"] == 0 and d["score"] is None
    assert d["insights"][0]["title"] == "Nothing logged yet" and d["streak"] == 0
    assert len(d["week"]["days"]) == 7 and d["week"]["days"][-1]["date"] == TODAY


def test_dashboard_totals(client):
    log(client, "oats", 50, "breakfast")
    log(client, "chicken-breast", 120, "lunch")
    log(client, "apple", 180, "snack")
    log(client, "apple", 180, "snack", day="2026-11-09")
    d = client.get("/api/dashboard?date=" + TODAY).get_json()
    assert d["totals"]["kcal"] == pytest.approx(194.5 + 198 + 93.6)
    assert set(d["per_meal"]) == {"breakfast", "lunch", "dinner", "snack"} and d["per_meal"]["dinner"] == 0
    assert d["remaining"]["kcal"] == pytest.approx(d["targets"]["kcal"] - d["totals"]["kcal"], abs=0.2)
    assert d["score"] >= 80 and d["grade"] == "A" and len(d["entries"]) == 3
    assert d["streak"] == 2 and d["week"]["summary"]["days_logged"] == 2
    assert d["suggestions"] and sum(d["macro_split"].values()) == 100


def test_weekly(client):
    log(client, "apple", 100, day="2026-11-08")
    w = client.get("/api/weekly?end=2026-11-10&days=3").get_json()
    assert [d["date"] for d in w["days"]] == ["2026-11-08", "2026-11-09", "2026-11-10"]
    assert w["summary"]["days_logged"] == 1
    assert client.get("/api/weekly?days=1").status_code == 400
    assert client.get("/api/dashboard?date=soon").status_code == 400


def test_demo_data_and_reset(client):
    r = post(client, "/api/demo", end=TODAY)
    assert r.status_code == 200 and r.get_json()["entries"] > 60
    d = client.get("/api/dashboard?date=" + TODAY).get_json()
    assert d["is_default"] is False and d["profile"]["name"] == "Demo user"
    assert d["score"] is not None and d["streak"] >= 3 and d["week"]["summary"]["days_logged"] >= 5
    assert len(client.get("/api/weight").get_json()) >= 10
    assert client.delete("/api/data").status_code == 200
    d = client.get("/api/dashboard?date=" + TODAY).get_json()
    assert d["is_default"] is True and d["totals"]["kcal"] == 0
    assert len(client.get("/api/foods").get_json()["foods"]) >= 70  # built-in foods stay


def test_demo_data_is_repeatable(client):
    post(client, "/api/demo", end=TODAY)
    first = client.get("/api/dashboard?date=" + TODAY).get_json()["totals"]
    post(client, "/api/demo", end=TODAY)
    assert client.get("/api/dashboard?date=" + TODAY).get_json()["totals"] == first


# ---- food safety checker ---------------------------------------------------
def test_safety_checker(client):
    r = post(client, "/api/safety/check", food={"name": "Cookie", "ingredients": ["peanut butter"]},
             allergies=["peanut"])
    assert r.status_code == 200 and r.get_json()["status"] == "unsafe"
    post(client, "/api/safety/check", food={"name": "Rice", "ingredients": ["rice"]})
    history = client.get("/api/safety/history").get_json()
    assert [h["food"]["name"] for h in history] == ["Rice", "Cookie"]
    assert history[1]["allergies"] == ["peanut"]
    assert client.get("/api/safety/stats").get_json() == {"safe": 1, "risky": 0, "unsafe": 1, "total": 2}
    assert client.delete("/api/safety/history").status_code == 200
    assert client.get("/api/safety/history").get_json() == []


@pytest.mark.parametrize("body", [
    {}, {"food": "rice"}, {"food": {"name": "  "}}, {"food": {"name": "x" * 101}},
    {"food": {"name": "X", "expiry_date": "tomorrow"}}, {"food": {"name": "X", "temperature_c": "abc"}},
])
def test_safety_validation(client, body):
    assert post(client, "/api/safety/check", **body).status_code == 400
    assert client.get("/api/safety/history").get_json() == []
