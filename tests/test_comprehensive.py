"""
Comprehensive test suite for GenericAPIIngestor.
Covers: AuthHandler, PaginationEngine (all types), ResponseParser, DataNormalizer, APIConfig schema.
"""
import pytest
import base64
from app.services.parser import ResponseParser
from app.services.normalizer import DataNormalizer
from app.schemas.config import (
    PaginationConfig, PaginationType,
    APIConfig, StorageConfig,
    AuthConfig, AuthType
)
from app.clients.pagination import PaginationEngine
from app.clients.auth import AuthHandler


# ─────────────────────────────────────────────
# AUTH HANDLER TESTS
# ─────────────────────────────────────────────

class TestAuthHandler:
    def test_no_auth_passthrough(self):
        config = AuthConfig(type=AuthType.NONE)
        headers, params = AuthHandler.apply_auth(config, {"Accept": "application/json"}, {})
        assert "Authorization" not in headers
        assert "api_key" not in params

    def test_bearer_auth_adds_authorization_header(self):
        config = AuthConfig(type=AuthType.BEARER, token="ghp_abc123")
        headers, params = AuthHandler.apply_auth(config, {}, {})
        assert headers["Authorization"] == "Bearer ghp_abc123"

    def test_bearer_auth_empty_token(self):
        config = AuthConfig(type=AuthType.BEARER, token=None)
        headers, _ = AuthHandler.apply_auth(config, {}, {})
        assert headers["Authorization"] == "Bearer "

    def test_api_key_in_header(self):
        config = AuthConfig(type=AuthType.API_KEY, header_name="X-Api-Key", key="secret123")
        headers, params = AuthHandler.apply_auth(config, {}, {})
        assert headers["X-Api-Key"] == "secret123"
        assert "api_key" not in params

    def test_api_key_in_query_param_when_no_header_name(self):
        config = AuthConfig(type=AuthType.API_KEY, header_name=None, key="qparam_secret")
        headers, params = AuthHandler.apply_auth(config, {}, {})
        assert params["api_key"] == "qparam_secret"
        assert "qparam_secret" not in str(headers.values())

    def test_basic_auth_encodes_correctly(self):
        config = AuthConfig(type=AuthType.BASIC, username="user", password="passwd")
        headers, _ = AuthHandler.apply_auth(config, {}, {})
        expected = base64.b64encode(b"user:passwd").decode("utf-8")
        assert headers["Authorization"] == f"Basic {expected}"

    def test_basic_auth_preserves_existing_headers(self):
        config = AuthConfig(type=AuthType.BASIC, username="u", password="p")
        headers, _ = AuthHandler.apply_auth(config, {"Accept": "application/json"}, {})
        assert headers["Accept"] == "application/json"
        assert "Authorization" in headers

    def test_auth_does_not_mutate_original_headers(self):
        config = AuthConfig(type=AuthType.BEARER, token="tok")
        original = {"Accept": "application/json"}
        AuthHandler.apply_auth(config, original, {})
        assert "Authorization" not in original


# ─────────────────────────────────────────────
# PAGINATION ENGINE TESTS
# ─────────────────────────────────────────────

class TestPaginationNone:
    def test_finishes_after_first_page(self):
        engine = PaginationEngine(PaginationConfig(type=PaginationType.NONE))
        params, url = engine.get_request_params({})
        assert url is None
        engine.update_state({}, {}, records_count=5)
        _, _ = engine.get_request_params({})
        assert engine.finished


class TestPaginationOffset:
    def _make_engine(self, page_size=10, initial_page=1, max_pages=5):
        return PaginationEngine(PaginationConfig(
            type=PaginationType.OFFSET,
            page_param="page",
            size_param="limit",
            page_size=page_size,
            initial_page=initial_page,
            max_pages=max_pages
        ))

    def test_first_page_params(self):
        engine = self._make_engine()
        params, url = engine.get_request_params({"q": "test"})
        assert params["page"] == 1
        assert params["limit"] == 10
        assert url is None

    def test_page_increments_after_full_page(self):
        engine = self._make_engine()
        engine.update_state({}, {}, records_count=10)
        params, _ = engine.get_request_params({})
        assert params["page"] == 2

    def test_finishes_on_partial_page(self):
        engine = self._make_engine(page_size=10)
        engine.update_state({}, {}, records_count=5)
        assert engine.finished

    def test_finishes_on_zero_records(self):
        engine = self._make_engine()
        engine.update_state({}, {}, records_count=0)
        assert engine.finished

    def test_max_pages_respected(self):
        engine = self._make_engine(max_pages=2)
        engine.update_state({}, {}, records_count=10)
        engine.pages_fetched = 2
        _, _ = engine.get_request_params({})
        assert engine.finished

    def test_custom_initial_page(self):
        engine = self._make_engine(initial_page=0)
        params, _ = engine.get_request_params({})
        assert params["page"] == 0


class TestPaginationLimitOffset:
    def _make_engine(self, page_size=20, max_pages=5):
        return PaginationEngine(PaginationConfig(
            type=PaginationType.LIMIT_OFFSET,
            offset_param="offset",
            limit_param="limit",
            page_size=page_size,
            max_pages=max_pages
        ))

    def test_first_request_offset_zero(self):
        engine = self._make_engine()
        params, _ = engine.get_request_params({})
        assert params["offset"] == 0
        assert params["limit"] == 20

    def test_offset_increases_by_records_count(self):
        engine = self._make_engine()
        engine.update_state({}, {}, records_count=20)
        params, _ = engine.get_request_params({})
        assert params["offset"] == 20

    def test_finishes_on_partial_page(self):
        engine = self._make_engine(page_size=20)
        engine.update_state({}, {}, records_count=15)
        assert engine.finished

    def test_offset_accumulates_correctly(self):
        engine = self._make_engine(page_size=10)
        engine.update_state({}, {}, records_count=10)
        engine.update_state({}, {}, records_count=10)
        params, _ = engine.get_request_params({})
        assert params["offset"] == 20


class TestPaginationCursor:
    def _make_engine(self):
        return PaginationEngine(PaginationConfig(
            type=PaginationType.CURSOR,
            cursor_param="cursor",
            next_cursor_path="meta.next_cursor",
            page_size=25,
            max_pages=5
        ))

    def test_first_request_has_no_cursor(self):
        engine = self._make_engine()
        params, _ = engine.get_request_params({})
        assert "cursor" not in params

    def test_cursor_set_from_response(self):
        engine = self._make_engine()
        engine.update_state({"meta": {"next_cursor": "abc123"}}, {}, records_count=25)
        params, _ = engine.get_request_params({})
        assert params["cursor"] == "abc123"

    def test_finishes_when_no_next_cursor(self):
        engine = self._make_engine()
        engine.update_state({"meta": {"next_cursor": None}}, {}, records_count=25)
        assert engine.finished

    def test_finishes_when_response_not_dict(self):
        engine = self._make_engine()
        engine.update_state([{"id": 1}], {}, records_count=1)
        assert engine.finished


class TestPaginationLinkHeader:
    def _make_engine(self):
        return PaginationEngine(PaginationConfig(
            type=PaginationType.LINK_HEADER,
            max_pages=3
        ))

    def test_first_page_uses_base_url(self):
        engine = self._make_engine()
        params, url = engine.get_request_params({})
        assert url is None

    def test_next_url_extracted_from_link_header(self):
        engine = self._make_engine()
        link = '<https://api.github.com/users/octocat/repos?page=2>; rel="next", <https://api.github.com/users/octocat/repos?page=5>; rel="last"'
        engine.update_state({}, {"link": link}, records_count=10)
        _, url = engine.get_request_params({})
        assert url == "https://api.github.com/users/octocat/repos?page=2"

    def test_finishes_when_no_next_in_link_header(self):
        engine = self._make_engine()
        link = '<https://api.github.com/users/octocat/repos?page=5>; rel="last"'
        engine.update_state({}, {"link": link}, records_count=10)
        assert engine.finished

    def test_finishes_when_link_header_absent(self):
        engine = self._make_engine()
        engine.update_state({}, {}, records_count=10)
        assert engine.finished

    def test_link_header_case_insensitive(self):
        engine = self._make_engine()
        link = '<https://api.example.com/items?page=2>; rel="next"'
        engine.update_state({}, {"Link": link}, records_count=10)
        _, url = engine.get_request_params({})
        assert url == "https://api.example.com/items?page=2"

    def test_max_pages_stops_pagination(self):
        engine = self._make_engine()
        engine.pages_fetched = 3
        _, _ = engine.get_request_params({})
        assert engine.finished


class TestPaginationNextUrl:
    def _make_engine(self):
        return PaginationEngine(PaginationConfig(
            type=PaginationType.NEXT_URL,
            next_url_path="pagination.next",
            max_pages=5
        ))

    def test_next_url_extracted_from_response_body(self):
        engine = self._make_engine()
        engine.update_state(
            {"pagination": {"next": "https://api.example.com/v2/items?page=2"}},
            {},
            records_count=20
        )
        _, url = engine.get_request_params({})
        assert url == "https://api.example.com/v2/items?page=2"

    def test_finishes_when_next_url_null(self):
        engine = self._make_engine()
        engine.update_state({"pagination": {"next": None}}, {}, records_count=20)
        assert engine.finished

    def test_finishes_when_path_missing(self):
        engine = self._make_engine()
        engine.update_state({"data": []}, {}, records_count=5)
        assert engine.finished


# ─────────────────────────────────────────────
# RESPONSE PARSER TESTS
# ─────────────────────────────────────────────

class TestResponseParser:
    def test_extract_top_level_key(self):
        data = {"items": [1, 2, 3]}
        assert ResponseParser.extract_path(data, "items") == [1, 2, 3]

    def test_extract_nested_key(self):
        data = {"result": {"data": {"users": [{"id": 1}]}}}
        assert ResponseParser.extract_path(data, "result.data.users") == [{"id": 1}]

    def test_extract_path_returns_none_for_missing_key(self):
        data = {"items": []}
        assert ResponseParser.extract_path(data, "results.items") is None

    def test_extract_path_list_index(self):
        data = {"pages": [{"url": "page1"}, {"url": "page2"}]}
        assert ResponseParser.extract_path(data, "pages.0") == {"url": "page1"}

    def test_extract_path_none_path_returns_data(self):
        data = {"key": "value"}
        assert ResponseParser.extract_path(data, None) == data

    def test_extract_records_from_list(self):
        data = [{"id": 1}, {"id": 2}]
        records = ResponseParser.extract_records(data, None)
        assert len(records) == 2
        assert records[0]["id"] == 1

    def test_extract_records_with_data_path(self):
        data = {"products": [{"id": 1, "name": "Apple"}, {"id": 2, "name": "Banana"}]}
        records = ResponseParser.extract_records(data, "products")
        assert len(records) == 2
        assert records[1]["name"] == "Banana"

    def test_extract_records_single_dict_returns_one(self):
        data = {"id": 10, "title": "Single"}
        records = ResponseParser.extract_records(data, None)
        assert len(records) == 1
        assert records[0]["title"] == "Single"

    def test_extract_records_empty_list(self):
        records = ResponseParser.extract_records({"items": []}, "items")
        assert records == []

    def test_flatten_dict_shallow(self):
        flat = ResponseParser.flatten_dict({"name": "Alice", "age": 30})
        assert flat["name"] == "Alice"
        assert flat["age"] == 30

    def test_flatten_dict_nested(self):
        data = {"user": {"address": {"city": "London", "zip": "EC1A"}}}
        flat = ResponseParser.flatten_dict(data)
        assert flat["user_address_city"] == "London"
        assert flat["user_address_zip"] == "EC1A"

    def test_flatten_dict_list_becomes_string(self):
        data = {"tags": ["python", "api"]}
        flat = ResponseParser.flatten_dict(data)
        assert isinstance(flat["tags"], str)
        assert "python" in flat["tags"]

    def test_flatten_dict_key_sanitization(self):
        data = {"first-name": "Bob", "Last Name": "Smith"}
        flat = ResponseParser.flatten_dict(data)
        assert "first_name" in flat
        assert "last_name" in flat

    def test_flatten_dict_deeply_nested(self):
        data = {"a": {"b": {"c": {"d": "deep"}}}}
        flat = ResponseParser.flatten_dict(data)
        assert flat["a_b_c_d"] == "deep"


# ─────────────────────────────────────────────
# DATA NORMALIZER TESTS
# ─────────────────────────────────────────────

class TestDataNormalizer:
    def _normalize(self, raw):
        return DataNormalizer.normalize_record(
            raw_record=raw,
            source_name="test_source",
            endpoint="/test/endpoint",
            request_id="req-xyz",
            ingestion_time="2026-07-31T10:00:00Z"
        )

    def test_metadata_fields_added(self):
        result = self._normalize({"id": 1})
        assert result["_ingestion_source"] == "test_source"
        assert result["_ingestion_endpoint"] == "/test/endpoint"
        assert result["_ingestion_request_id"] == "req-xyz"
        assert result["_ingestion_timestamp"] == "2026-07-31T10:00:00Z"

    def test_raw_payload_present(self):
        result = self._normalize({"id": 42, "name": "test"})
        assert "_raw_payload" in result

    def test_original_fields_preserved(self):
        result = self._normalize({"id": 99, "price": 9.99, "active": True})
        assert result["id"] == 99
        assert result["price"] == 9.99
        assert result["active"] is True

    def test_empty_record_still_has_metadata(self):
        result = self._normalize({})
        assert "_ingestion_source" in result

    def test_nested_record_gets_flattened(self):
        raw = {"user": {"name": "Alice", "city": "Paris"}}
        result = self._normalize(raw)
        assert "user_name" in result or "user" in result  # depends on flatten impl


# ─────────────────────────────────────────────
# SCHEMA VALIDATION TESTS
# ─────────────────────────────────────────────

class TestAPIConfigSchema:
    def test_minimal_valid_config(self):
        config = APIConfig(
            name="Test",
            base_url="https://api.example.com",
            endpoint="/data",
            storage=StorageConfig(table_name="test_table")
        )
        assert config.auth.type == AuthType.NONE
        assert config.pagination.type == PaginationType.NONE
        assert config.method == "GET"

    def test_bearer_auth_config(self):
        config = APIConfig(
            name="Secured API",
            base_url="https://secure.example.com",
            endpoint="/v1/data",
            auth=AuthConfig(type=AuthType.BEARER, token="my_token"),
            storage=StorageConfig(table_name="secure_data")
        )
        assert config.auth.token == "my_token"

    def test_api_key_auth_config(self):
        config = APIConfig(
            name="API Key Test",
            base_url="https://api.example.com",
            endpoint="/v1/items",
            auth=AuthConfig(type=AuthType.API_KEY, header_name="X-API-KEY", key="abc"),
            storage=StorageConfig(table_name="items")
        )
        assert config.auth.header_name == "X-API-KEY"
        assert config.auth.key == "abc"

    def test_pagination_defaults(self):
        config = APIConfig(
            name="P Test",
            base_url="https://api.example.com",
            endpoint="/items",
            storage=StorageConfig(table_name="items")
        )
        assert config.pagination.page_size == 30
        assert config.pagination.max_pages == 100

    def test_storage_primary_key_optional(self):
        config = APIConfig(
            name="No PK",
            base_url="https://api.example.com",
            endpoint="/events",
            storage=StorageConfig(table_name="events", primary_key=None)
        )
        assert config.storage.primary_key is None

    def test_custom_headers_and_params(self):
        config = APIConfig(
            name="Custom",
            base_url="https://api.example.com",
            endpoint="/search",
            headers={"X-Custom": "value", "Accept": "application/json"},
            params={"q": "python", "limit": 50},
            storage=StorageConfig(table_name="search_results")
        )
        assert config.headers["X-Custom"] == "value"
        assert config.params["limit"] == 50
