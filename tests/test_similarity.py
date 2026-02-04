import pytest
from app.core.similarity import (
    token_jaccard, edit_distance_similarity, exact_match,
    length_ratio, SimilarityScorer
)
from app.config.default import DEFAULT_CONFIG
from app.models.schemas import Record, NormalizedRecord

class TestTokenJaccard:
    def test_identical(self):
        assert token_jaccard(['a', 'b', 'c'], ['a', 'b', 'c']) == 1.0

    def test_disjoint(self):
        assert token_jaccard(['a', 'b'], ['c', 'd']) == 0.0

    def test_partial_overlap(self):
        result = token_jaccard(['a', 'b', 'c'], ['a', 'b', 'd'])
        assert 0.4 < result < 0.6  # 2/4 = 0.5

    def test_both_empty(self):
        assert token_jaccard([], []) == 1.0

    def test_one_empty(self):
        assert token_jaccard(['a'], []) == 0.0
        assert token_jaccard([], ['a']) == 0.0

class TestEditDistanceSimilarity:
    def test_identical(self):
        assert edit_distance_similarity("hello", "hello") == 1.0

    def test_completely_different(self):
        result = edit_distance_similarity("abc", "xyz")
        assert result < 0.5

    def test_typo(self):
        result = edit_distance_similarity("hello", "helo")
        assert result > 0.7

    def test_both_empty(self):
        assert edit_distance_similarity("", "") == 1.0

    def test_one_empty(self):
        assert edit_distance_similarity("hello", "") == 0.0
        assert edit_distance_similarity("", "hello") == 0.0

class TestExactMatch:
    def test_exact_match(self):
        assert exact_match("Drake", "Drake") == 1.0

    def test_case_insensitive(self):
        assert exact_match("Drake", "drake") == 1.0

    def test_different(self):
        assert exact_match("Drake", "Rihanna") == 0.0

    def test_missing_value(self):
        assert exact_match(None, "Drake") is None
        assert exact_match("Drake", None) is None
        assert exact_match("", "Drake") is None

class TestSimilarityScorer:
    @pytest.fixture
    def scorer(self):
        return SimilarityScorer(DEFAULT_CONFIG)

    def test_identical_records(self, scorer):
        record = Record(id="1", text="One Dance Drake", record_metadata={"artist": "Drake"}, source_row=1)
        norm = NormalizedRecord(
            record_id="1",
            tokens=["dance", "drake", "one"],
            normalized_text="one dance drake",
            original_record=record
        )

        score, signals, used = scorer.compute(norm, norm)
        assert score > 0.95
        assert len(used) > 0

    def test_weight_renormalization(self, scorer):
        """When a signal is missing, weights should renormalize."""
        record_a = Record(id="1", text="Test", record_metadata={}, source_row=1)
        record_b = Record(id="2", text="Test", record_metadata={}, source_row=2)

        norm_a = NormalizedRecord(record_id="1", tokens=["test"], normalized_text="test", original_record=record_a)
        norm_b = NormalizedRecord(record_id="2", tokens=["test"], normalized_text="test", original_record=record_b)

        score, signals, used = scorer.compute(norm_a, norm_b)

        # exact_field_match should be None (no artist)
        assert signals['exact_field_match'] is None
        assert 'exact_field_match' not in used
        # But score should still be valid
        assert score > 0.9
