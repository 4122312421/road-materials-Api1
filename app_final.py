import logging
import os
from contextlib import asynccontextmanager
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path as FilePath
from typing import Literal

from fastapi import FastAPI, HTTPException, Path, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


APP_VERSION = os.getenv("APP_VERSION", "0.1.0")
STATIC_DIR = FilePath(__file__).resolve().parent / "static"


class TariffSettings(BaseModel):
    rate: Decimal = Field(gt=0, max_digits=8, decimal_places=2)


DELIVERY_RATE = TariffSettings(
    rate=os.getenv("DELIVERY_RATE", "7.5")
).rate

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("road-materials-api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Starting RoadMaterials API, version=%s, delivery_rate=%s",
        APP_VERSION,
        DELIVERY_RATE,
    )
    yield
    logger.info("Stopping RoadMaterials API")


app = FastAPI(
    title="RoadMaterials API",
    description=(
        "Учебный каталог строительных материалов и расчёт доставки. "
        "Цены демонстрационные."
    ),
    version=APP_VERSION,
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Учебные данные: цена за одну тонну, в рублях.
MATERIALS = {
    1: {
        "id": 1,
        "name": "Асфальтобетонная смесь",
        "category": "asphalt",
        "price_per_ton": "10500.00",
        "currency": "RUB",
    },
    2: {
        "id": 2,
        "name": "Щебень 5-20",
        "category": "aggregate",
        "price_per_ton": "1600.00",
        "currency": "RUB",
    },
    3: {
        "id": 3,
        "name": "Песок",
        "category": "aggregate",
        "price_per_ton": "800.00",
        "currency": "RUB",
    },
}


# Ставки в рублях за тонно-километр. Грузоподъёмность выбирается
# отдельно от общего количества материала в заказе.
TARIFF_RATES = {
    63: {
        "over_100": "4.60",
        "from_20_to_100": "5.60",
        "under_20": "9.00",
        "special_1": "4.60",
        "special_2": "4.37",
    },
    53: {
        "over_100": "5.10",
        "from_20_to_100": "6.50",
        "under_20": "8.20",
        "special_1": "4.60",
        "special_2": "4.37",
    },
    42: {
        "over_100": "6.40",
        "from_20_to_100": "7.50",
        "under_20": "14.50",
        "special_1": "5.60",
        "special_2": "5.40",
    },
    32: {
        "over_100": "7.30",
        "from_20_to_100": "8.70",
        "under_20": "15.60",
        "special_1": "7.12",
        "special_2": "6.90",
    },
}
TARIFF_NAMES = {
    "default": "Базовый тариф",
    "standard": "Стандартный тариф",
    "special_1": "Спецтариф 1",
    "special_2": "Спецтариф 2",
}


class DeliveryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    material_id: int = Field(
        gt=0, strict=True, examples=[1], description="ID материала из каталога"
    )
    quantity_tons: Decimal = Field(
        gt=0,
        max_digits=10,
        decimal_places=3,
        examples=[30],
        description="Количество, т; до 3 знаков после точки",
    )
    distance_km: Decimal = Field(
        gt=0,
        max_digits=10,
        decimal_places=3,
        examples=[50],
        description="Расстояние доставки, км; до 3 знаков после точки",
    )
    tariff_mode: Literal["default", "standard", "special_1", "special_2"] = Field(
        default="default",
        description="Вид тарифа; default сохраняет тариф DELIVERY_RATE",
    )
    vehicle_capacity_tons: Literal[32, 42, 53, 63] | None = Field(
        default=None,
        description="Грузоподъёмность машины, т; обязательна для тарифа из таблицы",
    )
    origin: str = Field(
        default="", max_length=160, description="Откуда везут материал"
    )
    destination: str = Field(
        default="", max_length=160, description="Куда везут материал"
    )

    @field_validator("origin", "destination", mode="before")
    @classmethod
    def trim_route_point(cls, value):
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def require_capacity_for_table_tariff(self):
        if self.tariff_mode != "default" and self.vehicle_capacity_tons is None:
            raise ValueError("Выберите грузоподъёмность машины для тарифа из таблицы")
        return self


def find_material(material_id: int):
    material = MATERIALS.get(material_id)
    if material is None:
        raise HTTPException(status_code=404, detail="Материал не найден")
    return material


def round_money(amount: Decimal):
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def resolve_tariff(order: DeliveryRequest):
    if order.tariff_mode == "default":
        return DELIVERY_RATE, None, None

    band = None
    rate_key = order.tariff_mode
    if order.tariff_mode == "standard":
        # Обе границы 20 и 100 км относятся к среднему диапазону.
        if order.distance_km < Decimal("20"):
            band = "under_20"
        elif order.distance_km <= Decimal("100"):
            band = "from_20_to_100"
        else:
            band = "over_100"
        rate_key = band

    rate = Decimal(TARIFF_RATES[order.vehicle_capacity_tons][rate_key])
    return rate, band, order.vehicle_capacity_tons


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(STATIC_DIR / "index.html", media_type="text/html")


@app.get("/health", tags=["Служебные"])
def health():
    return {"status": "ok"}


@app.get("/version", tags=["Служебные"])
def version():
    return {"version": APP_VERSION}


@app.get("/pricing", tags=["Доставка"], summary="Действующий тариф доставки")
def pricing():
    return {"delivery_rate": str(DELIVERY_RATE), "currency": "RUB"}


@app.get("/tariffs", tags=["Доставка"], summary="Таблица тарифов перевозки")
def tariffs():
    return {
        "currency": "RUB",
        "unit": "RUB_PER_TON_KM",
        "default_rate": str(DELIVERY_RATE),
        "rows": [
            {"vehicle_capacity_tons": capacity, "rates": rates}
            for capacity, rates in TARIFF_RATES.items()
        ],
    }


@app.get("/materials", tags=["Материалы"], summary="Список материалов")
def list_materials(
    category: str | None = Query(
        default=None, description="Категория: asphalt или aggregate"
    ),
):
    materials = list(MATERIALS.values())
    if category is not None:
        materials = [m for m in materials if m["category"] == category]
    return materials


@app.get(
    "/materials/{material_id}",
    tags=["Материалы"],
    summary="Материал по ID",
)
def get_material(material_id: int = Path(gt=0)):
    return find_material(material_id)


@app.post(
    "/delivery/calculate",
    tags=["Доставка"],
    summary="Стоимость материала и доставки",
)
def calculate_delivery(order: DeliveryRequest):
    material = find_material(order.material_id)
    price = Decimal(material["price_per_ton"])
    rate, distance_band, capacity = resolve_tariff(order)

    material_cost = round_money(price * order.quantity_tons)
    delivery_cost = round_money(
        rate * order.quantity_tons * order.distance_km
    )
    total_cost = material_cost + delivery_cost

    logger.info(
        "Delivery calculated: material_id=%s, quantity_tons=%s, "
        "distance_km=%s, tariff_mode=%s, vehicle_capacity_tons=%s, "
        "delivery_rate=%s, total_cost=%s RUB",
        order.material_id,
        order.quantity_tons,
        order.distance_km,
        order.tariff_mode,
        capacity,
        rate,
        total_cost,
    )

    return {
        "material_id": material["id"],
        "material_name": material["name"],
        "quantity_tons": str(order.quantity_tons),
        "distance_km": str(order.distance_km),
        "price_per_ton": material["price_per_ton"],
        "delivery_rate": str(rate),
        "tariff_mode": order.tariff_mode,
        "tariff_name": TARIFF_NAMES[order.tariff_mode],
        "vehicle_capacity_tons": capacity,
        "distance_band": distance_band,
        "origin": order.origin,
        "destination": order.destination,
        "material_cost": str(material_cost),
        "delivery_cost": str(delivery_cost),
        "total_cost": str(total_cost),
        "currency": "RUB",
    }
