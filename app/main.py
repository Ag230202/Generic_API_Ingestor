from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import logging

from app.api.endpoints import router as api_router
from app.utils.exceptions import DatabaseUnavailableError, UpstreamAPIError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

app = FastAPI(
    title="Generic Data Ingestion Service",
    description="Configuration-driven ingestion service for arbitrary REST APIs into PostgreSQL.",
    version="1.0.0"
)


@app.exception_handler(DatabaseUnavailableError)
async def db_unavailable_handler(request: Request, exc: DatabaseUnavailableError):
    logging.error(f"503 DB Unavailable: {exc}")
    return JSONResponse(
        status_code=503,
        content={"detail": "Service Unavailable", "message": str(exc)}
    )


@app.exception_handler(UpstreamAPIError)
async def upstream_api_handler(request: Request, exc: UpstreamAPIError):
    logging.error(f"502 Upstream API Error: {exc}")
    return JSONResponse(
        status_code=502,
        content={"detail": "Bad Gateway", "message": str(exc)}
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.error(f"500 Unhandled Error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "message": str(exc)}
    )


app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def root():
    return {
        "service": "Generic Data Ingestion Service",
        "status": "running",
        "docs": "/docs"
    }
