from datetime import date, timedelta

import pytest
from fastapi import HTTPException

from app.filters import Period, resolve_date_range

TODAY = date(2026, 10, 15)


# ---------- unit tests: pure function, fixed "today" ----------
@pytest.mark.parametrize(
    "period, days",
    [(Period.week, 7), (Period.month, 30), (Period.three_months, 90)],
)
def test_period_ranges(period, days):
    start, end = resolve_date_range(period, None, None, today=TODAY)
    assert start == TODAY - timedelta(days=days)
    assert end == TODAY


def test_no_filters_means_no_limits():
    assert resolve_date_range(None, None, None, today=TODAY) == (None, None)


def test_custom_range_passes_through():
    s, e = date(2026, 9, 1), date(2026, 9, 30)
    assert resolve_date_range(None, s, e, today=TODAY) == (s, e)


def test_open_ended_custom_ranges():
    s = date(2026, 9, 1)
    assert resolve_date_range(None, s, None, today=TODAY) == (s, None)
    assert resolve_date_range(None, None, s, today=TODAY) == (None, s)


def test_period_and_custom_dates_conflict():
    with pytest.raises(HTTPException) as exc:
        resolve_date_range(Period.week, date(2026, 10, 1), None, today=TODAY)
    assert exc.value.status_code == 400


def test_reversed_range_rejected():
    with pytest.raises(HTTPException) as exc:
        resolve_date_range(None, date(2026, 10, 10), date(2026, 10, 1), today=TODAY)
    assert exc.value.status_code == 400


# ---------- integration tests through the API ----------
def days_ago(n):
    return (date.today() - timedelta(days=n)).isoformat()


def seed(client, headers, offsets):
    for n in offsets:
        r = client.post(
            "/expenses",
            json={"title": f"{n}d", "amount": "10.00", "category": "Others", "date": days_ago(n)},
            headers=headers,
        )
        assert r.status_code == 201


def titles(response):
    assert response.status_code == 200, response.text
    return {e["title"] for e in response.json()}


def test_period_filters(client, make_user):
    h = make_user()
    seed(client, h, [0, 3, 20, 60, 120])
    assert titles(client.get("/expenses?period=week", headers=h)) == {"0d", "3d"}
    assert titles(client.get("/expenses?period=month", headers=h)) == {"0d", "3d", "20d"}
    assert titles(client.get("/expenses?period=3months", headers=h)) == {"0d", "3d", "20d", "60d"}
    assert len(client.get("/expenses", headers=h).json()) == 5


def test_period_boundary_is_inclusive(client, make_user):
    h = make_user()
    seed(client, h, [7, 8])
    assert titles(client.get("/expenses?period=week", headers=h)) == {"7d"}


def test_custom_range(client, make_user):
    h = make_user()
    seed(client, h, [0, 3, 20, 60])
    url = f"/expenses?start_date={days_ago(25)}&end_date={days_ago(10)}"
    assert titles(client.get(url, headers=h)) == {"20d"}
    assert titles(client.get(f"/expenses?start_date={days_ago(5)}", headers=h)) == {"0d", "3d"}
    assert titles(client.get(f"/expenses?end_date={days_ago(30)}", headers=h)) == {"60d"}


def test_invalid_filter_combinations(client, make_user):
    h = make_user()
    assert client.get(f"/expenses?period=week&start_date={days_ago(5)}", headers=h).status_code == 400
    assert client.get(f"/expenses?start_date={days_ago(1)}&end_date={days_ago(5)}", headers=h).status_code == 400
    assert client.get("/expenses?start_date=hello", headers=h).status_code == 422
    assert client.get("/expenses?period=year", headers=h).status_code == 422


def test_filters_never_leak_other_users(client, make_user):
    alice = make_user("alice@example.com")
    bob = make_user("bob@example.com")
    seed(client, alice, [0, 3])
    assert client.get("/expenses?period=week", headers=bob).json() == []