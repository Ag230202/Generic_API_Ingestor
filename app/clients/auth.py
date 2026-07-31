from typing import Dict
import base64
from app.schemas.config import AuthConfig, AuthType


class AuthHandler:
    @staticmethod
    def apply_auth(auth_config: AuthConfig, headers: Dict[str, str], params: Dict[str, str]) -> tuple[Dict[str, str], Dict[str, str]]:
        headers_copy = headers.copy()
        params_copy = params.copy()

        if auth_config.type == AuthType.API_KEY:
            if auth_config.header_name:
                headers_copy[auth_config.header_name] = auth_config.key or ""
            else:
                params_copy["api_key"] = auth_config.key or ""

        elif auth_config.type == AuthType.BEARER:
            headers_copy["Authorization"] = f"Bearer {auth_config.token or ''}"

        elif auth_config.type == AuthType.BASIC:
            credentials = f"{auth_config.username or ''}:{auth_config.password or ''}"
            encoded = base64.b64encode(credentials.encode()).decode("utf-8")
            headers_copy["Authorization"] = f"Basic {encoded}"

        return headers_copy, params_copy
