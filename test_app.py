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
    assert result["tariff_mode"] == "default"
    assert result["tariff_name"] == "Базовый тариф"
    assert result["vehicle_capacity_tons"] is None
    assert result["distance_band"] is None
    assert result["origin"] == result["destination"] == ""


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


def test_user_interface(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert 'id="estimate-form"' in response.text
    assert "/static/styles.css" in response.text
    assert "/static/app.js" in response.text


@pytest.mark.parametrize(
    "path, content_types, marker",
    [
        ("/static/styles.css", ("text/css",), ":root"),
        (
            "/static/app.js",
            ("text/javascript", "application/javascript"),
            "/delivery/calculate",
        ),
    ],
)
def test_interface_assets(client, path, content_types, marker):
    response = client.get(path)
    assert response.status_code == 200
    assert response.headers["content-type"].split(";")[0] in content_types
    assert marker in response.text


@pytest.mark.parametrize("client", ["7.5", "8"], indirect=True)
def test_pricing_matches_calculation(client, valid_order):
    pricing_response = client.get("/pricing")
    calculation_response = client.post("/delivery/calculate", json=valid_order)
    assert pricing_response.status_code == 200
    assert calculation_response.status_code == 200
    pricing_data = pricing_response.json()
    result = calculation_response.json()
    assert pricing_data == {
        "delivery_rate": result["delivery_rate"],
        "currency": result["currency"],
    }


def test_tariff_table(client):
    response = client.get("/tariffs")
    assert response.status_code == 200
    table = response.json()
    assert table["currency"] == "RUB"
    assert table["unit"] == "RUB_PER_TON_KM"
    assert table["default_rate"] == "7.5"
    columns = [
        "over_100", "from_20_to_100", "under_20", "special_1", "special_2"
    ]
    # Контрольные значения из тарифной таблицы, независимо от кода приложения.
    expected = {
        63: ["4.60", "5.60", "9.00", "4.60", "4.37"],
        53: ["5.10", "6.50", "8.20", "4.60", "4.37"],
        42: ["6.40", "7.50", "14.50", "5.60", "5.40"],
        32: ["7.30", "8.70", "15.60", "7.12", "6.90"],
    }
    assert [row["vehicle_capacity_tons"] for row in table["rows"]] == list(expected)
    for row in table["rows"]:
        assert [row["rates"][key] for key in columns] == expected[
            row["vehicle_capacity_tons"]
        ]


@pytest.mark.parametrize(
    "capacity, mode, distance, expected_rate, expected_delivery",
    [
        (63, "standard", 150, "4.60", "20700.00"),
        (63, "standard", 50, "5.60", "8400.00"),
        (63, "standard", 10, "9.00", "2700.00"),
        (63, "special_1", 50, "4.60", "6900.00"),
        (63, "special_2", 50, "4.37", "6555.00"),
        (53, "standard", 150, "5.10", "22950.00"),
        (53, "standard", 50, "6.50", "9750.00"),
        (53, "standard", 10, "8.20", "2460.00"),
        (53, "special_1", 50, "4.60", "6900.00"),
        (53, "special_2", 50, "4.37", "6555.00"),
        (42, "standard", 150, "6.40", "28800.00"),
        (42, "standard", 50, "7.50", "11250.00"),
        (42, "standard", 10, "14.50", "4350.00"),
        (42, "special_1", 50, "5.60", "8400.00"),
        (42, "special_2", 50, "5.40", "8100.00"),
        (32, "standard", 150, "7.30", "32850.00"),
        (32, "standard", 50, "8.70", "13050.00"),
        (32, "standard", 10, "15.60", "4680.00"),
        (32, "special_1", 50, "7.12", "10680.00"),
        (32, "special_2", 50, "6.90", "10350.00"),
    ],
)
def test_table_tariff_calculation(
    client, valid_order, capacity, mode, distance, expected_rate, expected_delivery
):
    valid_order.update(
        tariff_mode=mode,
        vehicle_capacity_tons=capacity,
        distance_km=distance,
    )
    response = client.post("/delivery/calculate", json=valid_order)
    assert response.status_code == 200
    result = response.json()
    assert result["delivery_rate"] == expected_rate
    assert result["delivery_cost"] == expected_delivery
    assert result["material_cost"] == "315000.00"
    assert result["tariff_mode"] == mode
    assert result["vehicle_capacity_tons"] == capacity
    assert result["tariff_name"] == {
        "standard": "Стандартный тариф",
        "special_1": "Спецтариф 1",
        "special_2": "Спецтариф 2",
    }[mode]


@pytest.mark.parametrize(
    "distance, band, rate, delivery",
    [
        ("19.999", "under_20", "14.50", "8699.57"),
        ("20", "from_20_to_100", "7.50", "4500.00"),
        ("100", "from_20_to_100", "7.50", "22500.00"),
        ("100.001", "over_100", "6.40", "19200.19"),
    ],
)
def test_standard_tariff_boundaries(client, valid_order, distance, band, rate, delivery):
    valid_order.update(
        tariff_mode="standard", vehicle_capacity_tons=42, distance_km=distance
    )
    response = client.post("/delivery/calculate", json=valid_order)
    assert response.status_code == 200
    result = response.json()
    assert result["distance_band"] == band
    assert result["delivery_rate"] == rate
    assert result["delivery_cost"] == delivery


@pytest.mark.parametrize("mode, rate", [("special_1", "4.60"), ("special_2", "4.37")])
def test_special_tariff_does_not_change_with_distance(client, valid_order, mode, rate):
    valid_order.update(tariff_mode=mode, vehicle_capacity_tons=63)
    for distance in (10, 150):
        valid_order["distance_km"] = distance
        response = client.post("/delivery/calculate", json=valid_order)
        assert response.status_code == 200
        result = response.json()
        assert result["delivery_rate"] == rate
        assert result["distance_band"] is None


@pytest.mark.parametrize(
    "extra",
    [
        {"tariff_mode": "standard"},
        {"tariff_mode": "special_1"},
        {"tariff_mode": "special_2"},
        {"tariff_mode": "unknown", "vehicle_capacity_tons": 42},
        {"tariff_mode": "standard", "vehicle_capacity_tons": 50},
        {"tariff_mode": "standard", "vehicle_capacity_tons": "42"},
        {"delivery_rate": "0.01"},
    ],
)
def test_invalid_tariff_parameters(client, valid_order, extra):
    valid_order.update(extra)
    response = client.post("/delivery/calculate", json=valid_order)
    assert response.status_code == 422


def test_route_is_trimmed_and_does_not_change_cost(client, valid_order):
    valid_order.update(
        origin="  Уфа, производственная база  ",
        destination="  Салават, строительная площадка  ",
    )
    response = client.post("/delivery/calculate", json=valid_order)
    assert response.status_code == 200
    result = response.json()
    assert result["origin"] == "Уфа, производственная база"
    assert result["destination"] == "Салават, строительная площадка"
    assert result["delivery_cost"] == "11250.00"
    assert result["total_cost"] == "326250.00"


@pytest.mark.parametrize("field", ["origin", "destination"])
def test_route_length_limit(client, valid_order, field):
    valid_order[field] = "А" * 160
    assert client.post("/delivery/calculate", json=valid_order).status_code == 200
    valid_order[field] += "Б"
    response = client.post("/delivery/calculate", json=valid_order)
    assert response.status_code == 422
    assert any(error["loc"][-1] == field for error in response.json()["detail"])


def test_special_tariff_rounding(client, valid_order):
    valid_order.update(
        tariff_mode="special_2",
        vehicle_capacity_tons=63,
        quantity_tons="2.5",
        distance_km="0.3",
    )
    response = client.post("/delivery/calculate", json=valid_order)
    assert response.status_code == 200
    result = response.json()
    assert result["delivery_rate"] == "4.37"
    assert result["delivery_cost"] == "3.28"
    assert result["total_cost"] == "26253.28"


@pytest.mark.parametrize("client", ["8"], indirect=True)
def test_table_tariff_is_independent_of_default_rate(client, valid_order):
    table = client.get("/tariffs").json()
    assert table["default_rate"] == "8"
    valid_order.update(tariff_mode="standard", vehicle_capacity_tons=42)
    response = client.post("/delivery/calculate", json=valid_order)
    assert response.status_code == 200
    assert response.json()["delivery_rate"] == "7.50"
    assert response.json()["delivery_cost"] == "11250.00"
