import logging
import os
from contextlib import asynccontextmanager
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path as FilePath

from fastapi import FastAPI, HTTPException, Path, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field


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


def find_material(material_id: int):
    material = MATERIALS.get(material_id)
    if material is None:
        raise HTTPException(status_code=404, detail="Материал не найден")
    return material


def round_money(amount: Decimal):
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


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

    material_cost = round_money(price * order.quantity_tons)
    delivery_cost = round_money(
        DELIVERY_RATE * order.quantity_tons * order.distance_km
    )
    total_cost = material_cost + delivery_cost

    logger.info(
        "Delivery calculated: material_id=%s, quantity_tons=%s, "
        "distance_km=%s, total_cost=%s RUB",
        order.material_id,
        order.quantity_tons,
        order.distance_km,
        total_cost,
    )

    return {
        "material_id": material["id"],
        "material_name": material["name"],
        "quantity_tons": str(order.quantity_tons),
        "distance_km": str(order.distance_km),
        "price_per_ton": material["price_per_ton"],
        "delivery_rate": str(DELIVERY_RATE),
        "material_cost": str(material_cost),
        "delivery_cost": str(delivery_cost),
        "total_cost": str(total_cost),
        "currency": "RUB",
    }
