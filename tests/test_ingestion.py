import pytest
from app.services.parser import ResponseParser
from app.services.normalizer import DataNormalizer
from app.schemas.config import PaginationConfig, PaginationType, APIConfig, StorageConfig
from app.clients.pagination import PaginationEngine


def test_extract_path_nested():
    data = {"result": {"items": [{"id": 1, "name": "item1"}, {"id": 2, "name": "item2"}]}}
    extracted = ResponseParser.extract_path(data, "result.items")
    assert isinstance(extracted, list)
    assert len(extracted) == 2
    assert extracted[0]["name"] == "item1"


def test_extract_records_fallback():
    data = {"id": 10, "title": "Test Title"}
    records = ResponseParser.extract_records(data, None)
    assert len(records) == 1
    assert records[0]["title"] == "Test Title"


def test_flatten_dict():
    nested = {
        "user": {
            "name": "Alice",
            "address": {
                "city": "New York",
                "zip": "10001"
            }
        },
        "tags": ["admin", "staff"]
    }
    flattened = ResponseParser.flatten_dict(nested)
    assert flattened["user_name"] == "Alice"
    assert flattened["user_address_city"] == "New York"
    assert flattened["user_address_zip"] == "10001"
    assert flattened["tags"] == "['admin', 'staff']"


def test_data_normalizer():
    raw_record = {"id": 101, "price": 99.99}
    normalized = DataNormalizer.normalize_record(
        raw_record=raw_record,
        source_name="test_source",
        endpoint="/test",
        request_id="req123",
        ingestion_time="2026-07-30T18:00:00Z"
    )
    assert normalized["id"] == 101
    assert normalized["price"] == 99.99
    assert normalized["_ingestion_source"] == "test_source"
    assert normalized["_ingestion_endpoint"] == "/test"
    assert normalized["_ingestion_request_id"] == "req123"
    assert "_raw_payload" in normalized


def test_pagination_offset_engine():
    config = PaginationConfig(
        type=PaginationType.OFFSET,
        page_param="page",
        size_param="size",
        page_size=10,
        initial_page=1
    )
    engine = PaginationEngine(config)
    params, url_override = engine.get_request_params({"q": "search"})
    assert params["page"] == 1
    assert params["size"] == 10
    assert not engine.finished

    engine.update_state({}, {}, records_count=10)
    params, _ = engine.get_request_params({"q": "search"})
    assert params["page"] == 2

    # Return less records -> finish
    engine.update_state({}, {}, records_count=5)
    assert engine.finished


def test_api_config_schema_validation():
    config_data = {
        "name": "Test API",
        "base_url": "https://api.example.com",
        "endpoint": "/v1/data",
        "storage": {
            "table_name": "test_table",
            "primary_key": "id"
        }
    }
    config = APIConfig(**config_data)
    assert config.name == "Test API"
    assert config.storage.table_name == "test_table"
    assert config.auth.type == "none"
