from fastapi import APIRouter, HTTPException, Depends
from app.schemas.config import IngestionRequest, IngestionResponse
from app.services.ingestion import IngestionController
from app.storage.postgres import PostgresStorage
from app.database.session import engine

router = APIRouter()


def get_ingestion_controller() -> IngestionController:
    storage = PostgresStorage(engine=engine)
    return IngestionController(storage=storage)


@router.post("/ingest", response_model=IngestionResponse)
async def ingest_data(
    payload: IngestionRequest,
    controller: IngestionController = Depends(get_ingestion_controller)
):
    """
    Ingests data from one or more generic API source configurations.
    """
    if not payload.sources:
        raise HTTPException(status_code=400, detail="No sources provided in request payload.")

    return await controller.run_ingestion(payload.sources)
