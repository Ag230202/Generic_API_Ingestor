from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseStorage(ABC):
    @abstractmethod
    async def save_records(
        self,
        table_name: str,
        records: List[Dict[str, Any]],
        primary_key: str = None
    ) -> int:
        """Saves normalized records to target storage and returns count of saved records."""
        pass
