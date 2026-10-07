import pytest

from app.main import app


@pytest.fixture()
def client():
    app.config.update(TESTING=True)
    return app.test_client()


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_calc_add(client):
    resp = client.get("/api/calc?op=add&a=10&b=5")
    assert resp.status_code == 200
    assert resp.get_json()["result"] == 15


def test_calc_divide_by_zero_is_400(client):
    resp = client.get("/api/calc?op=divide&a=1&b=0")
    assert resp.status_code == 400
    assert "zero" in resp.get_json()["error"]


def test_calc_unknown_op_is_400(client):
    assert client.get("/api/calc?op=pow&a=2&b=3").status_code == 400


def test_calc_non_numeric_is_400(client):
    assert client.get("/api/calc?op=add&a=x&b=3").status_code == 400
