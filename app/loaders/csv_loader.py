import csv
import io
from typing import Dict, List, Tuple
from app.loaders.base import BaseLoader
from app.models.schemas import Record
import uuid

class CsvLoader(BaseLoader):
    def validate(self, file_content: bytes) -> Tuple[bool, List[str]]:
        errors = []
        try:
            content = file_content.decode('utf-8')
            reader = csv.reader(io.StringIO(content))
            header = next(reader, None)
            if not header:
                errors.append("CSV file is empty or has no header row")
            elif len(header) < 1:
                errors.append("CSV must have at least one column")
        except UnicodeDecodeError:
            errors.append("File is not valid UTF-8 encoded text")
        except csv.Error as e:
            errors.append(f"CSV parsing error: {e}")

        return len(errors) == 0, errors

    def load(
        self,
        file_content: bytes,
        column_mapping: Dict[str, str]
    ) -> Tuple[List[Record], List[str]]:
        records = []
        warnings = []

        content = file_content.decode('utf-8')
        reader = csv.DictReader(io.StringIO(content))

        text_column = column_mapping.get('text', 'text')
        id_column = column_mapping.get('id', 'id')

        for row_num, row in enumerate(reader, start=2):  # Start at 2 (1-indexed + header)
            # Skip completely empty rows
            if not any(row.values()):
                warnings.append(f"Row {row_num}: Skipped empty row")
                continue

            # Get text field (required)
            text = row.get(text_column, '').strip()
            if not text:
                warnings.append(f"Row {row_num}: Missing required text field '{text_column}'")
                continue

            # Get or generate ID
            record_id = row.get(id_column, '').strip()
            if not record_id:
                record_id = f"rec_{uuid.uuid4().hex[:8]}"
                warnings.append(f"Row {row_num}: Generated ID '{record_id}' (no ID column)")

            # Collect remaining fields as metadata
            metadata = {}
            for key, value in row.items():
                if key not in [text_column, id_column] and value:
                    mapped_key = next(
                        (k for k, v in column_mapping.items() if v == key),
                        key
                    )
                    metadata[mapped_key] = value.strip()

            records.append(Record(
                id=record_id,
                text=text,
                record_metadata=metadata,
                source_row=row_num
            ))

        return records, warnings
