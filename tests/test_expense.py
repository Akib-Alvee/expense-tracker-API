from decimal import Decimal

SAMPLE = {"title": "Weekly shop", "amount": "45.30", "category": "Groceries", "date": "2026-10-10"}


def create(client, headers, **overrides):
    r = client.post("/expenses", json={**SAMPLE, **overrides}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def test_requires_auth(client):
    assert client.get("/expenses").status_code == 401
    assert client.post("/expenses", json=SAMPLE).status_code == 401
    assert client.patch("/expenses/1", json={"title": "x"}).status_code == 401
    assert client.delete("/expenses/1").status_code == 401


def test_create_and_get(client, make_user):
    h = make_user()
    created = create(client, h)
    assert Decimal(str(created["amount"])) == Decimal("45.30")
    r = client.get(f"/expenses/{created['id']}", headers=h)
    assert r.status_code == 200
    assert r.json()["title"] == "Weekly shop"


def test_create_rejects_invalid_input(client, make_user):
    h = make_user()
    for bad in (
        {"category": "Food"},
        {"amount": "-5"},
        {"amount": "0"},
        {"title": ""},
        {"date": "2026-13-45"},
    ):
        r = client.post("/expenses", json={**SAMPLE, **bad}, headers=h)
        assert r.status_code == 422, bad


def test_user_id_in_body_is_ignored(client, make_user):
    h = make_user()
    r = client.post("/expenses", json={**SAMPLE, "user_id": 999}, headers=h)
    assert r.status_code == 201
    assert "user_id" not in r.json()


def test_list_is_newest_first(client, make_user):
    h = make_user()
    create(client, h, title="old", date="2026-01-01")
    create(client, h, title="new", date="2026-06-01")
    titles = [e["title"] for e in client.get("/expenses", headers=h).json()]
    assert titles == ["new", "old"]


def test_patch_updates_only_sent_fields(client, make_user):
    h = make_user()
    e = create(client, h, description="keep me")
    r = client.patch(f"/expenses/{e['id']}", json={"amount": "20.00"}, headers=h)
    assert r.status_code == 200
    body = r.json()
    assert Decimal(str(body["amount"])) == Decimal("20.00")
    assert body["title"] == "Weekly shop"
    assert body["description"] == "keep me"


def test_patch_can_clear_description_but_not_required_fields(client, make_user):
    h = make_user()
    e = create(client, h, description="temp")
    assert client.patch(f"/expenses/{e['id']}", json={"description": None}, headers=h).json()["description"] is None
    assert client.patch(f"/expenses/{e['id']}", json={"title": None}, headers=h).status_code == 422


def test_delete(client, make_user):
    h = make_user()
    e = create(client, h)
    assert client.delete(f"/expenses/{e['id']}", headers=h).status_code == 204
    assert client.get(f"/expenses/{e['id']}", headers=h).status_code == 404


def test_missing_and_malformed_ids(client, make_user):
    h = make_user()
    assert client.get("/expenses/9999", headers=h).status_code == 404
    assert client.get("/expenses/abc", headers=h).status_code == 422


def test_ownership_isolation(client, make_user):
    alice = make_user("alice@example.com")
    bob = make_user("bob@example.com")
    e = create(client, alice)

    # Bob can't read, change, or delete Alice's expense, and can't tell it exists
    assert client.get(f"/expenses/{e['id']}", headers=bob).status_code == 404
    assert client.patch(f"/expenses/{e['id']}", json={"title": "hacked"}, headers=bob).status_code == 404
    assert client.delete(f"/expenses/{e['id']}", headers=bob).status_code == 404
    assert client.get("/expenses", headers=bob).json() == []

    # ...and Alice's expense is untouched
    mine = client.get(f"/expenses/{e['id']}", headers=alice).json()
    assert mine["title"] == "Weekly shop"