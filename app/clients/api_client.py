from typing import Dict, Any, Tuple
import httpx
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.schemas.config import APIConfig
from app.clients.auth import AuthHandler

logger = logging.getLogger(__name__)


class GenericAPIClient:
    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout

    async def fetch_page(
        self,
        config: APIConfig,
        params: Dict[str, Any],
        url_override: str = None
    ) -> Tuple[Any, Dict[str, str]]:
        headers, query_params = AuthHandler.apply_auth(config.auth, config.headers, params)
        
        target_url = url_override if url_override else f"{config.base_url.rstrip('/')}/{config.endpoint.lstrip('/')}"

        return await self._execute_with_retry(
            method=config.method,
            url=target_url,
            headers=headers,
            params=query_params
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True
    )
    async def _execute_with_retry(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        params: Dict[str, Any]
    ) -> Tuple[Any, Dict[str, str]]:
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            logger.info(f"Executing HTTP {method} request to {url}")
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                params=params
            )
            response.raise_for_status()
            response_json = response.json()
            response_headers = dict(response.headers)
            return response_json, response_headers
