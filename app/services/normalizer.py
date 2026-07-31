from typing import Dict, Any, List
from datetime import datetime, timezone
import json
import uuid
from app.services.parser import ResponseParser


class DataNormalizer:
    @staticmethod
    def normalize_record(
        raw_record: Dict[str, Any],
        source_name: str,
        endpoint: str,
        request_id: str,
        ingestion_time: str
    ) -> Dict[str, Any]:
        flattened = ResponseParser.flatten_dict(raw_record)
        
        # Inject metadata
        flattened["_ingestion_source"] = source_name
        flattened["_ingestion_endpoint"] = endpoint
        flattened["_ingestion_request_id"] = request_id
        flattened["_ingestion_timestamp"] = ingestion_time
        flattened["_raw_payload"] = json.dumps(raw_record)
        
        return flattened

    @classmethod
    def normalize_batch(
        cls,
        records: List[Dict[str, Any]],
        source_name: str,
        endpoint: str,
        request_id: str
    ) -> List[Dict[str, Any]]:
        ingestion_time = datetime.now(timezone.utc).isoformat()
        return [
            cls.normalize_record(rec, source_name, endpoint, request_id, ingestion_time)
            for rec in records
        ]
