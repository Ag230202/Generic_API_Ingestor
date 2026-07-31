from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class AuthType(str, Enum):
    NONE = "none"
    API_KEY = "api_key"
    BEARER = "bearer"
    BASIC = "basic"


class AuthConfig(BaseModel):
    type: AuthType = AuthType.NONE
    header_name: Optional[str] = "X-API-Key"
    key: Optional[str] = None
    token: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None


class PaginationType(str, Enum):
    NONE = "none"
    OFFSET = "offset"
    CURSOR = "cursor"
    NEXT_URL = "next_url"
    LIMIT_OFFSET = "limit_offset"
    LINK_HEADER = "link_header"


class PaginationConfig(BaseModel):
    type: PaginationType = PaginationType.NONE
    page_param: Optional[str] = "page"
    size_param: Optional[str] = "limit"
    page_size: int = 30
    initial_page: int = 1
    offset_param: Optional[str] = "skip"
    limit_param: Optional[str] = "limit"
    cursor_param: Optional[str] = "cursor"
    next_cursor_path: Optional[str] = "next_cursor"
    next_url_path: Optional[str] = "next"
    max_pages: Optional[int] = 100


class StorageConfig(BaseModel):
    table_name: str
    primary_key: Optional[str] = None


class APIConfig(BaseModel):
    name: str
    base_url: str
    endpoint: str
    method: str = "GET"
    headers: Dict[str, str] = Field(default_factory=dict)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    params: Dict[str, Any] = Field(default_factory=dict)
    pagination: PaginationConfig = Field(default_factory=PaginationConfig)
    data_path: Optional[str] = None
    storage: StorageConfig


class IngestionRequest(BaseModel):
    sources: list[APIConfig]


class IngestionResult(BaseModel):
    source_name: str
    status: str
    records_ingested: int
    duration_seconds: float
    error: Optional[str] = None


class IngestionResponse(BaseModel):
    total_sources: int
    total_records: int
    total_duration_seconds: float
    results: list[IngestionResult]
