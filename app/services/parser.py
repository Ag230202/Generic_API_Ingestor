from typing import Any, Dict, List, Optional


class ResponseParser:
    @staticmethod
    def extract_path(data: Any, path: Optional[str]) -> Any:
        if not path or not data:
            return data
        
        parts = path.split(".")
        current = data
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            elif isinstance(current, list) and part.isdigit():
                idx = int(part)
                if 0 <= idx < len(current):
                    current = current[idx]
                else:
                    return None
            else:
                return None
        return current

    @staticmethod
    def extract_records(data: Any, data_path: Optional[str] = None) -> List[Dict[str, Any]]:
        extracted = ResponseParser.extract_path(data, data_path)
        if isinstance(extracted, list):
            return [item if isinstance(item, dict) else {"value": item} for item in extracted]
        elif isinstance(extracted, dict):
            return [extracted]
        return []

    @staticmethod
    def flatten_dict(d: Dict[str, Any], parent_key: str = "", sep: str = "_") -> Dict[str, Any]:
        items: List[tuple[str, Any]] = []
        for k, v in d.items():
            # Sanitize key name for SQL column compatibility
            clean_k = str(k).replace("-", "_").replace(" ", "_").lower()
            new_key = f"{parent_key}{sep}{clean_k}" if parent_key else clean_k
            
            if isinstance(v, dict):
                items.extend(ResponseParser.flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, list):
                # Convert list to string or simple representation for DB persistence
                items.append((new_key, str(v)))
            else:
                items.append((new_key, v))
        return dict(items)
