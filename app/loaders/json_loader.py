import json
from typing import Dict, List, Tuple
from app.loaders.base import BaseLoader
from app.models.schemas import Record
import uuid

class JsonLoader(BaseLoader):
    def validate(self, file_content: bytes) -> Tuple[bool, List[str]]:
        errors = []
        try:
            content = file_content.decode('utf-8')
            # Try parsing as JSON array
            data = json.loads(content)
            if not isinstance(data, list):
                errors.append("JSON must be an array of objects")
            elif len(data) == 0:
                errors.append("JSON array is empty")
            elif not all(isinstance(item, dict) for item in data):
                errors.append("All items in JSON array must be objects")
        except UnicodeDecodeError:
            errors.append("File is not valid UTF-8 encoded text")
        except json.JSONDecodeError as e:
            # Try newline-delimited JSON
            try:
                lines = content.strip().split('\n')
                for i, line in enumerate(lines):
                    json.loads(line)
            except json.JSONDecodeError:
                errors.append(f"Invalid JSON: {e}")

        return len(errors) == 0, errors

    def load(
        self,
        file_content: bytes,
        column_mapping: Dict[str, str]
    ) -> Tuple[List[Record], List[str]]:
        records = []
        warnings = []

        content = file_content.decode('utf-8')

        # Try JSON array first, then newline-delimited
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            data = [json.loads(line) for line in content.strip().split('\n')]

        text_field = column_mapping.get('text', 'text')
        id_field = column_mapping.get('id', 'id')

        for row_num, item in enumerate(data, start=1):
            # Get text field (required)
            text = str(item.get(text_field, '')).strip()
            if not text:
                warnings.append(f"Item {row_num}: Missing required text field '{text_field}'")
                continue

            # Get or generate ID
            record_id = str(item.get(id_field, '')).strip()
            if not record_id:
                record_id = f"rec_{uuid.uuid4().hex[:8]}"
                warnings.append(f"Item {row_num}: Generated ID '{record_id}'")

            # Collect remaining fields as metadata
            metadata = {}
            for key, value in item.items():
                if key not in [text_field, id_field] and value is not None:
                    mapped_key = next(
                        (k for k, v in column_mapping.items() if v == key),
                        key
                    )
                    metadata[mapped_key] = value

            records.append(Record(
                id=record_id,
                text=text,
                record_metadata=metadata,
                source_row=row_num
            ))

        return records, warnings
