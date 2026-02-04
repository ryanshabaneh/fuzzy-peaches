from typing import List, Set, Optional, Tuple, Dict
from rapidfuzz import fuzz
from app.models.schemas import NormalizedRecord
from app.config.schemas import ResolverConfig, SimilarityWeights

def token_jaccard(tokens_a: List[str], tokens_b: List[str]) -> float:
    """
    Jaccard similarity: |intersection| / |union|

    Returns 1.0 if both empty (vacuously similar).
    Returns 0.0 if one empty and other non-empty.
    """
    set_a = set(tokens_a)
    set_b = set(tokens_b)

    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0

    intersection = len(set_a & set_b)
    union = len(set_a | set_b)

    return intersection / union


def edit_distance_similarity(str_a: str, str_b: str) -> float:
    """
    Normalized edit distance similarity using rapidfuzz.

    Returns 1.0 if both empty.
    Returns 0.0 if one empty and other non-empty.
    Uses fuzz.ratio which returns 0-100, normalized to 0-1.
    """
    if not str_a and not str_b:
        return 1.0
    if not str_a or not str_b:
        return 0.0

    # fuzz.ratio returns 0-100
    return fuzz.ratio(str_a, str_b) / 100.0


def exact_match(val_a: Optional[str], val_b: Optional[str]) -> Optional[float]:
    """
    Exact match comparison.

    Returns None if either value is None/empty (signal not computable).
    Returns 1.0 if equal, 0.0 if different.
    """
    if not val_a or not val_b:
        return None  # Signal not computable

    return 1.0 if val_a.lower().strip() == val_b.lower().strip() else 0.0


def numeric_similarity(
    num_a: Optional[float],
    num_b: Optional[float],
    tolerance: float = 5.0
) -> Optional[float]:
    """
    Numeric similarity with tolerance and decay.

    Returns None if either value is None.
    Returns 1.0 if within tolerance.
    Decays exponentially beyond tolerance.
    """
    if num_a is None or num_b is None:
        return None

    diff = abs(num_a - num_b)
    if diff <= tolerance:
        return 1.0

    # Exponential decay beyond tolerance
    return max(0.0, 1.0 - (diff - tolerance) / (tolerance * 2))


def length_ratio(str_a: str, str_b: str) -> float:
    """
    Length similarity: min_length / max_length

    Returns 1.0 if both empty.
    Returns 0.0 if one empty and other non-empty.
    """
    len_a = len(str_a)
    len_b = len(str_b)

    if len_a == 0 and len_b == 0:
        return 1.0
    if len_a == 0 or len_b == 0:
        return 0.0

    return min(len_a, len_b) / max(len_a, len_b)


class SimilarityScorer:
    """
    Computes weighted similarity between normalized records.

    Handles missing data by:
    1. Only including computable signals
    2. Renormalizing weights to sum to 1.0

    This prevents records with missing fields from being unfairly penalized.
    """

    def __init__(self, config: ResolverConfig):
        self.weights = config.weights
        self.config = config

    def compute(
        self,
        record_a: NormalizedRecord,
        record_b: NormalizedRecord
    ) -> Tuple[float, Dict[str, float], List[str]]:
        """
        Compute weighted similarity.

        Returns:
            Tuple of (final_score, signals_dict, signals_used)
            - final_score: Weighted combination of computable signals
            - signals_dict: All signal values (None if not computable)
            - signals_used: List of signal names that contributed to score
        """
        # Compute all signals
        signals = {
            'token_jaccard': token_jaccard(record_a.tokens, record_b.tokens),
            'edit_distance': edit_distance_similarity(
                record_a.normalized_text,
                record_b.normalized_text
            ),
            'exact_field_match': exact_match(
                record_a.original_record.record_metadata.get('artist'),
                record_b.original_record.record_metadata.get('artist')
            ),
            'length_ratio': length_ratio(
                record_a.normalized_text,
                record_b.normalized_text
            )
        }

        # Identify computable signals and their weights
        computable = {}
        for signal_name, value in signals.items():
            if value is not None:
                weight = getattr(self.weights, signal_name)
                computable[signal_name] = (value, weight)

        signals_used = list(computable.keys())

        if not computable:
            # No signals computable - return 0 with warning
            return 0.0, signals, []

        # Renormalize weights to sum to 1.0
        total_weight = sum(w for _, w in computable.values())

        # Compute weighted sum with renormalized weights
        final_score = sum(
            value * (weight / total_weight)
            for value, weight in computable.values()
        )

        return final_score, signals, signals_used
