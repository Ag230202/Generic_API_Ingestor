import time
import uuid
import logging
from typing import List
import httpx
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from app.schemas.config import APIConfig, IngestionResult, IngestionResponse
from app.clients.api_client import GenericAPIClient
from app.clients.pagination import PaginationEngine
from app.services.parser import ResponseParser
from app.services.normalizer import DataNormalizer
from app.storage.base import BaseStorage
from app.utils.exceptions import DatabaseUnavailableError, UpstreamAPIError

logger = logging.getLogger(__name__)


class IngestionController:
    def __init__(self, storage: BaseStorage):
        self.storage = storage
        self.client = GenericAPIClient()

    async def process_source(self, config: APIConfig) -> IngestionResult:
        start_time = time.time()
        request_id = str(uuid.uuid4())[:8]
        total_records_saved = 0
        pagination = PaginationEngine(config.pagination)

        logger.info(f"[{request_id}] Starting ingestion for source: {config.name}")

        try:
            while not pagination.finished:
                params, url_override = pagination.get_request_params(config.params)
                if pagination.finished:
                    break

                try:
                    response_data, response_headers = await self.client.fetch_page(
                        config, params, url_override
                    )
                except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError, httpx.UnsupportedProtocol) as e:
                    raise UpstreamAPIError(f"External API call failed for '{config.name}': {e}") from e

                raw_records = ResponseParser.extract_records(response_data, config.data_path)
                records_count = len(raw_records)

                if records_count > 0:
                    normalized_records = DataNormalizer.normalize_batch(
                        raw_records,
                        source_name=config.name,
                        endpoint=config.endpoint,
                        request_id=request_id
                    )

                    try:
                        saved_count = await self.storage.save_records(
                            table_name=config.storage.table_name,
                            records=normalized_records,
                            primary_key=config.storage.primary_key
                        )
                    except (OperationalError, SQLAlchemyError, OSError, ConnectionRefusedError) as e:
                        raise DatabaseUnavailableError(f"Database unavailable: {e}") from e

                    total_records_saved += saved_count

                pagination.update_state(response_data, response_headers, records_count)

            duration = round(time.time() - start_time, 2)
            logger.info(f"[{request_id}] Finished source '{config.name}': {total_records_saved} records in {duration}s")
            return IngestionResult(
                source_name=config.name,
                status="success",
                records_ingested=total_records_saved,
                duration_seconds=duration
            )

        except (DatabaseUnavailableError, UpstreamAPIError):
            raise  # Re-raise to endpoint for proper HTTP status code

        except Exception as e:
            logger.error(f"[{request_id}] Unexpected error for '{config.name}': {e}", exc_info=True)
            raise  # Unhandled → 500

    async def run_ingestion(self, sources: List[APIConfig]) -> IngestionResponse:
        start_time = time.time()
        results = []
        total_records = 0

        for config in sources:
            res = await self.process_source(config)
            results.append(res)
            total_records += res.records_ingested

        total_duration = round(time.time() - start_time, 2)
        return IngestionResponse(
            total_sources=len(sources),
            total_records=total_records,
            total_duration_seconds=total_duration,
            results=results
        )
