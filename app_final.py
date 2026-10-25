import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI


APP_VERSION = os.getenv("APP_VERSION", "0.1.0")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("road-materials-api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting RoadMaterials API, version=%s", APP_VERSION)
    yield
    logger.info("Stopping RoadMaterials API")


app = FastAPI(
    title="RoadMaterials API",
    description="Каталог строительных материалов и расчёт доставки.",
    version=APP_VERSION,
    lifespan=lifespan,
)


@app.get("/health", tags=["Служебные"])
def health():
    return {"status": "ok"}


@app.get("/version", tags=["Служебные"])
def version():
    return {"version": APP_VERSION}
