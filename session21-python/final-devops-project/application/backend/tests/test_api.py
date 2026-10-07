from datetime import date


def test_health(client):
    assert client.get("/health").json() == {"status": "UP"}


def test_ready_checks_database(client):
    resp = client.get("/ready")
    assert resp.status_code == 200
    assert resp.json() == {"status": "READY"}


def test_root_identifies_service(client):
    assert client.get("/").json()["service"] == "SpendWise API"


def test_create_expense(client):
    resp = client.post("/api/expenses", json={"title": "Metro card", "amount": "500", "category": "TRANSPORT"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "Metro card"
    assert body["category"] == "TRANSPORT"
    assert body["spent_on"] == date.today().isoformat()


def test_create_rejects_non_positive_amount(client):
    resp = client.post("/api/expenses", json={"title": "Refund?", "amount": "0"})
    assert resp.status_code == 422


def test_create_rejects_unknown_category(client):
    resp = client.post("/api/expenses", json={"title": "Gold", "amount": "10", "category": "CRYPTO"})
    assert resp.status_code == 422


def test_list_and_get(client, expense):
    assert [e["id"] for e in client.get("/api/expenses").json()] == [expense["id"]]
    assert client.get(f"/api/expenses/{expense['id']}").json()["title"] == "Groceries"


def test_filter_by_category_and_month(client, expense):
    client.post("/api/expenses", json={"title": "Movie", "amount": "300", "category": "ENTERTAINMENT", "spent_on": "2026-09-15"})
    assert len(client.get("/api/expenses", params={"category": "food"}).json()) == 1
    assert len(client.get("/api/expenses", params={"month": "2026-09"}).json()) == 1
    assert client.get("/api/expenses", params={"month": "2026-9"}).status_code == 422


def test_update_expense(client, expense):
    resp = client.put(f"/api/expenses/{expense['id']}", json={"amount": "999.99", "note": "monthly stock-up"})
    assert resp.status_code == 200
    assert resp.json()["amount"] == "999.99"
    assert resp.json()["title"] == "Groceries"


def test_delete_expense(client, expense):
    assert client.delete(f"/api/expenses/{expense['id']}").status_code == 204
    assert client.get(f"/api/expenses/{expense['id']}").status_code == 404


def test_missing_expense_is_404(client):
    assert client.get("/api/expenses/12345").status_code == 404
    assert client.put("/api/expenses/12345", json={"title": "x"}).status_code == 404


def test_summary(client, expense):
    client.post("/api/expenses", json={"title": "Rent", "amount": "15000", "category": "RENT", "spent_on": "2026-10-02"})
    s = client.get("/api/expenses/summary").json()
    assert s["count"] == 2
    assert s["total"] == "16250.50"
    assert s["top_category"] == "RENT"
    assert {c["category"] for c in s["by_category"]} == {"FOOD", "RENT"}


def test_metrics_exposes_business_counter(client, expense):
    body = client.get("/metrics").text
    assert 'spendwise_expenses_created_total{category="FOOD"}' in body
    assert "http_request_duration_seconds" in body
