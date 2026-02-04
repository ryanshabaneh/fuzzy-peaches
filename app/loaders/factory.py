from typing import Tuple
from app.loaders.base import BaseLoader
from app.loaders.csv_loader import CsvLoader
from app.loaders.json_loader import JsonLoader

def get_loader(filename: str, file_content: bytes) -> Tuple[BaseLoader, str]:
    """
    Detect file type and return appropriate loader.

    Returns:
        Tuple of (loader_instance, detected_format)

    Raises:
        ValueError if format cannot be determined
    """
    # Try extension first
    lower_name = filename.lower()
    if lower_name.endswith('.csv'):
        return CsvLoader(), 'csv'
    elif lower_name.endswith('.json') or lower_name.endswith('.jsonl'):
        return JsonLoader(), 'json'

    # Content sniffing fallback
    try:
        content = file_content.decode('utf-8').strip()
        if content.startswith('[') or content.startswith('{'):
            return JsonLoader(), 'json'
        elif ',' in content.split('\n')[0]:
            return CsvLoader(), 'csv'
    except:
        pass

    raise ValueError(
        f"Cannot determine file format for '{filename}'. "
        "Supported formats: .csv, .json, .jsonl"
    )
