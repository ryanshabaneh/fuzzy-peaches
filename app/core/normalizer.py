import re
import unicodedata
from typing import List
from app.models.schemas import Record, NormalizedRecord
from app.config.schemas import ResolverConfig

class Normalizer:
    # Abbreviation expansions
    ABBREVIATIONS = {
        'feat.': 'featuring',
        'feat': 'featuring',
        'ft.': 'featuring',
        'ft': 'featuring',
        '&': 'and',
        '+': 'and',
        'w/': 'with',
        'vs.': 'versus',
        'vs': 'versus',
    }

    def __init__(self, config: ResolverConfig):
        self.stopwords = set(word.lower() for word in config.stopwords)

    def clean_text(self, text: str) -> str:
        """
        Clean and normalize text.
        - Lowercase
        - Expand abbreviations
        - Remove accents (NFD normalization)
        - Remove punctuation
        - Collapse whitespace
        """
        if not text:
            return ""

        # Lowercase
        text = text.lower()

        # Expand abbreviations
        for abbrev, expansion in self.ABBREVIATIONS.items():
            pattern = r'\b' + re.escape(abbrev) + r'\b'
            text = re.sub(pattern, expansion, text)

        # Unicode normalization - decompose accents then remove combining marks
        # café → cafe
        text = unicodedata.normalize('NFD', text)
        text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')

        # Remove punctuation except spaces
        text = re.sub(r'[^\w\s]', ' ', text)

        # Collapse multiple spaces
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def tokenize(self, text: str) -> List[str]:
        """
        Tokenize and filter.
        - Split on whitespace
        - Remove stopwords
        - Sort alphabetically (order-independent matching)
        """
        if not text:
            return []

        tokens = text.split()

        # Remove stopwords
        tokens = [t for t in tokens if t not in self.stopwords]

        # Sort for order-independent comparison
        # "Drake One Dance" matches "One Dance Drake"
        tokens = sorted(tokens)

        return tokens

    def normalize_record(self, record: Record) -> NormalizedRecord:
        """Process a full record."""
        cleaned = self.clean_text(record.text)
        tokens = self.tokenize(cleaned)

        return NormalizedRecord(
            record_id=record.id,
            tokens=tokens,
            normalized_text=cleaned,
            original_record=record
        )
