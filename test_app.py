import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch, request):
    rate = getattr(request, "param", "7.5")
    monkeypatch.setenv("APP_VERSION", "0.1.0")
    monkeypatch.setenv("DELIVERY_RATE", rate)

    import app_final

    module = importlib.reload(app_final)
    with TestClient(module.app) as test_client:
        yield test_client


@pytest.fixture
def valid_order():
    return {
        "material_id": 1,
        "quantity_tons": 30,
        "distance_km": 50,
    }


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_version(client):
    response = client.get("/version")
    assert response.status_code == 200
    assert response.json() == {"version": "0.1.0"}


def test_materials_list(client):
    response = client.get("/materials")
    assert response.status_code == 200
    materials = response.json()
    assert len(materials) == 3
    assert {item["id"] for item in materials} == {1, 2, 3}


def test_materials_category_filter(client):
    response = client.get("/materials", params={"category": "aggregate"})
    assert response.status_code == 200
    materials = response.json()
    assert len(materials) == 2
    assert {item["id"] for item in materials} == {2, 3}
    assert all(item["category"] == "aggregate" for item in materials)


def test_material_by_id(client):
    response = client.get("/materials/1")
    assert response.status_code == 200
    material = response.json()
    assert material["id"] == 1
    assert material["price_per_ton"] == "10500.00"
    assert material["currency"] == "RUB"


def test_unknown_material(client):
    response = client.get("/materials/999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Материал не найден"}


def test_delivery_calculation(client, valid_order):
    response = client.post("/delivery/calculate", json=valid_order)
    assert response.status_code == 200
    result = response.json()
    assert result["delivery_rate"] == "7.5"
    assert result["material_cost"] == "315000.00"
    assert result["delivery_cost"] == "11250.00"
    assert result["total_cost"] == "326250.00"
    assert result["currency"] == "RUB"


def test_delivery_rounding(client, valid_order):
    valid_order["quantity_tons"] = 2.5
    valid_order["distance_km"] = 0.3
    response = client.post("/delivery/calculate", json=valid_order)
    assert response.status_code == 200
    result = response.json()
    assert result["material_cost"] == "26250.00"
    assert result["delivery_cost"] == "5.63"
    assert result["total_cost"] == "26255.63"


def test_delivery_unknown_material(client, valid_order):
    valid_order["material_id"] = 999
    response = client.post("/delivery/calculate", json=valid_order)
    assert response.status_code == 404
    assert response.json() == {"detail": "Материал не найден"}


def test_delivery_zero_quantity(client, valid_order):
    valid_order["quantity_tons"] = 0
    response = client.post("/delivery/calculate", json=valid_order)
    assert response.status_code == 422
    assert any(
        error["loc"][-1] == "quantity_tons"
        for error in response.json()["detail"]
    )


def test_delivery_negative_distance(client, valid_order):
    valid_order["distance_km"] = -10
    response = client.post("/delivery/calculate", json=valid_order)
    assert response.status_code == 422
    assert any(
        error["loc"][-1] == "distance_km"
        for error in response.json()["detail"]
    )


@pytest.mark.parametrize("client", ["8"], indirect=True)
def test_delivery_tariff_from_environment(client, valid_order):
    response = client.post("/delivery/calculate", json=valid_order)
    assert response.status_code == 200
    result = response.json()
    assert result["delivery_rate"] == "8"
    assert result["material_cost"] == "315000.00"
    assert result["delivery_cost"] == "12000.00"
    assert result["total_cost"] == "327000.00"
