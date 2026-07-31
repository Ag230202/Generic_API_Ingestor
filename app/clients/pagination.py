from typing import Dict, Any, Optional, Tuple
import re
from app.schemas.config import PaginationConfig, PaginationType
from app.services.parser import ResponseParser


class PaginationEngine:
    def __init__(self, config: PaginationConfig):
        self.config = config
        self.current_page = config.initial_page
        self.current_offset = 0
        self.next_url: Optional[str] = None
        self.current_cursor: Optional[str] = None
        self.finished = False
        self.pages_fetched = 0

    def get_request_params(self, base_params: Dict[str, Any]) -> Tuple[Dict[str, Any], Optional[str]]:
        params = base_params.copy()
        url_override = None

        if self.config.type == PaginationType.NONE:
            if self.pages_fetched > 0:
                self.finished = True
            return params, url_override

        if self.pages_fetched >= (self.config.max_pages or 100):
            self.finished = True
            return params, url_override

        if self.config.type == PaginationType.OFFSET:
            params[self.config.page_param] = self.current_page
            if self.config.size_param:
                params[self.config.size_param] = self.config.page_size

        elif self.config.type == PaginationType.LIMIT_OFFSET:
            params[self.config.offset_param] = self.current_offset
            params[self.config.limit_param] = self.config.page_size

        elif self.config.type == PaginationType.CURSOR:
            if self.current_cursor:
                params[self.config.cursor_param] = self.current_cursor
            if self.config.size_param:
                params[self.config.size_param] = self.config.page_size

        elif self.config.type in (PaginationType.NEXT_URL, PaginationType.LINK_HEADER):
            if self.pages_fetched > 0:
                if self.next_url:
                    url_override = self.next_url
                else:
                    self.finished = True

        return params, url_override

    def update_state(self, response_data: Any, headers: Dict[str, str], records_count: int) -> None:
        self.pages_fetched += 1

        if records_count == 0:
            self.finished = True
            return

        if self.config.type == PaginationType.OFFSET:
            self.current_page += 1
            if records_count < self.config.page_size:
                self.finished = True

        elif self.config.type == PaginationType.LIMIT_OFFSET:
            self.current_offset += records_count
            if records_count < self.config.page_size:
                self.finished = True

        elif self.config.type == PaginationType.CURSOR:
            if isinstance(response_data, dict) and self.config.next_cursor_path:
                next_cursor = ResponseParser.extract_path(response_data, self.config.next_cursor_path)
                if next_cursor:
                    self.current_cursor = str(next_cursor)
                else:
                    self.finished = True
            else:
                self.finished = True

        elif self.config.type == PaginationType.NEXT_URL:
            if isinstance(response_data, dict) and self.config.next_url_path:
                next_url = ResponseParser.extract_path(response_data, self.config.next_url_path)
                if next_url and isinstance(next_url, str):
                    self.next_url = next_url
                else:
                    self.finished = True
            else:
                self.finished = True

        elif self.config.type == PaginationType.LINK_HEADER:
            link_header = headers.get("link") or headers.get("Link")
            if link_header:
                match = re.search(r'<([^>]+)>;\s*rel="next"', link_header)
                if match:
                    self.next_url = match.group(1)
                else:
                    self.finished = True
            else:
                self.finished = True
