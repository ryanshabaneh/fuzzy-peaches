import pytest
from app.core.normalizer import Normalizer
from app.config.schemas import ResolverConfig
from app.config.default import DEFAULT_CONFIG
from app.models.schemas import Record

@pytest.fixture
def normalizer():
    return Normalizer(DEFAULT_CONFIG)

class TestCleanText:
    def test_lowercase(self, normalizer):
        assert normalizer.clean_text("HELLO World") == "hello world"

    def test_punctuation_removal(self, normalizer):
        assert normalizer.clean_text("hello, world!") == "hello world"

    def test_unicode_normalization(self, normalizer):
        assert normalizer.clean_text("café") == "cafe"
        assert normalizer.clean_text("naïve") == "naive"

    def test_abbreviation_expansion(self, normalizer):
        assert "featuring" in normalizer.clean_text("Drake feat. Rihanna")
        assert "featuring" in normalizer.clean_text("Drake ft. Rihanna")
        assert normalizer.clean_text("Tom & Jerry") == "tom jerry"

    def test_whitespace_collapse(self, normalizer):
        assert normalizer.clean_text("hello    world") == "hello world"

    def test_empty_string(self, normalizer):
        assert normalizer.clean_text("") == ""

class TestTokenize:
    def test_basic_tokenization(self, normalizer):
        tokens = normalizer.tokenize("one dance drake")
        assert tokens == ["dance", "drake", "one"]  # Sorted

    def test_stopword_removal(self, normalizer):
        tokens = normalizer.tokenize("one dance radio edit")
        assert "radio" not in tokens
        assert "edit" not in tokens

    def test_empty_string(self, normalizer):
        assert normalizer.tokenize("") == []

    def test_all_stopwords(self, normalizer):
        tokens = normalizer.tokenize("feat radio edit remix")
        assert tokens == []  # All removed

class TestNormalizeRecord:
    def test_full_normalization(self, normalizer):
        record = Record(
            id="1",
            text="Drake – One Dance (feat. Wizkid)",
            record_metadata={"artist": "Drake"},
            source_row=1
        )
        normalized = normalizer.normalize_record(record)

        assert normalized.record_id == "1"
        assert set(normalized.tokens) == {"dance", "drake", "one", "wizkid"}
        assert normalized.original_record == record
