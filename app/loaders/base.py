from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Any
from app.models.schemas import Record

class BaseLoader(ABC):
    @abstractmethod
    def load(
        self,
        file_content: bytes,
        column_mapping: Dict[str, str]
    ) -> Tuple[List[Record], List[str]]:
        """
        Load records from file content.

        Args:
            file_content: Raw bytes of the file
            column_mapping: Maps internal field names to file column names
                           e.g., {"text": "song_title", "artist": "performer"}

        Returns:
            Tuple of (records, warnings)
            - records: Successfully parsed Record objects
            - warnings: Non-fatal issues encountered during parsing
        """
        pass

    @abstractmethod
    def validate(self, file_content: bytes) -> Tuple[bool, List[str]]:
        """
        Validate file content before loading.

        Returns:
            Tuple of (is_valid, errors)
        """
        pass
