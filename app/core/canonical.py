from typing import Dict, Set, Tuple, List
from app.models.schemas import Record, NormalizedRecord, Entity
from app.core.similarity import SimilarityScorer
from app.core.grouping import MatchGraph
import re

def compute_completeness(record: Record) -> float:
    """
    Score based on non-null metadata fields.
    More complete records are better representatives.
    """
    if not record.record_metadata:
        return 0.0

    total_fields = len(record.record_metadata)
    non_null = sum(1 for v in record.record_metadata.values() if v)

    return non_null / total_fields if total_fields > 0 else 0.0


def compute_cleanliness(record: Record) -> float:
    """
    Score based on text cleanliness.
    Shorter, simpler text is considered cleaner.
    """
    text = record.text
    if not text:
        return 0.0

    # Penalize length (normalize to ~100 chars)
    length_penalty = min(1.0, 100 / max(len(text), 1))

    # Penalize special characters
    special_chars = len(re.findall(r'[^\w\s]', text))
    special_penalty = max(0.0, 1.0 - special_chars / 10)

    # Penalize ALL CAPS
    caps_ratio = sum(1 for c in text if c.isupper()) / max(len(text), 1)
    caps_penalty = 1.0 if caps_ratio < 0.5 else 0.5

    return (length_penalty + special_penalty + caps_penalty) / 3


def compute_centrality(
    record_id: str,
    group: Set[str],
    normalized_records: Dict[str, NormalizedRecord],
    scorer: SimilarityScorer
) -> float:
    """
    Score based on average similarity to other group members.
    Central records are better representatives.
    """
    if len(group) <= 1:
        return 1.0

    record = normalized_records.get(record_id)
    if not record:
        return 0.0

    total_score = 0.0
    comparisons = 0

    for other_id in group:
        if other_id == record_id:
            continue

        other = normalized_records.get(other_id)
        if not other:
            continue

        score, _, _ = scorer.compute(record, other)
        total_score += score
        comparisons += 1

    return total_score / comparisons if comparisons > 0 else 0.0


def select_canonical(
    group: Set[str],
    records: Dict[str, Record],
    normalized_records: Dict[str, NormalizedRecord],
    scorer: SimilarityScorer
) -> Tuple[str, Dict[str, float]]:
    """
    Select the best record as canonical representative.

    Criteria (weighted):
    - Completeness (40%): More metadata fields
    - Cleanliness (30%): Shorter, cleaner text
    - Centrality (30%): Higher average similarity to group

    Returns:
        (canonical_record_id, selection_scores)
    """
    if len(group) == 1:
        record_id = list(group)[0]
        return record_id, {"completeness": 1.0, "cleanliness": 1.0, "centrality": 1.0}

    scores = {}

    for record_id in group:
        record = records.get(record_id)
        if not record:
            continue

        completeness = compute_completeness(record)
        cleanliness = compute_cleanliness(record)
        centrality = compute_centrality(record_id, group, normalized_records, scorer)

        # Weighted combination
        total = 0.4 * completeness + 0.3 * cleanliness + 0.3 * centrality

        scores[record_id] = {
            "completeness": completeness,
            "cleanliness": cleanliness,
            "centrality": centrality,
            "total": total
        }

    # Handle empty scores (all records missing from dict)
    if not scores:
        record_id = sorted(group)[0]
        return record_id, {
            "completeness": 0.0,
            "cleanliness": 0.0,
            "centrality": 0.0,
            "total": 0.0,
        }

    # Select highest total score
    best_id = max(scores.keys(), key=lambda x: scores[x]["total"])

    return best_id, scores[best_id]
