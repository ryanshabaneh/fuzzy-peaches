from typing import Set, List, Dict, Tuple
from collections import defaultdict
from app.models.schemas import NormalizedRecord
from app.config.schemas import BlockingConfig

def generate_block_keys(
    record: NormalizedRecord,
    config: BlockingConfig
) -> Set[str]:
    """
    Generate blocking keys based on configured strategies.
    Records sharing a block key will be compared.

    Edge case: If normalized_text is shorter than min_key_length,
    no key is generated for that strategy (record can still match via other keys).
    """
    keys = set()

    for strategy in config.strategies:
        if strategy == "first_3_chars":
            text = record.normalized_text
            if len(text) >= config.min_key_length:
                keys.add(f"f3:{text[:3]}")

        elif strategy == "first_token":
            if record.tokens:
                keys.add(f"ft:{record.tokens[0]}")

        elif strategy == "artist":
            artist = record.original_record.record_metadata.get('artist', '')
            if artist:
                keys.add(f"art:{artist.lower().strip()}")

        elif strategy == "year":
            year = record.original_record.record_metadata.get('year')
            if year:
                keys.add(f"yr:{year}")

    return keys


def get_candidate_pairs(
    records: List[NormalizedRecord],
    config: BlockingConfig
) -> Tuple[List[Tuple[str, str]], int, List[str]]:
    """
    Get pairs to compare based on blocking.

    Returns:
        (candidate_pairs, total_possible_pairs, warnings)
    """
    warnings = []
    total_possible = len(records) * (len(records) - 1) // 2

    if not config.enabled:
        # Return all pairs
        pairs = []
        for i in range(len(records)):
            for j in range(i + 1, len(records)):
                pairs.append((records[i].record_id, records[j].record_id))
        return pairs, total_possible, warnings

    # Build inverted index: block_key -> record_ids
    block_index: Dict[str, Set[str]] = defaultdict(set)
    records_without_keys = []

    for record in records:
        keys = generate_block_keys(record, config)
        if not keys:
            records_without_keys.append(record.record_id)
        for key in keys:
            block_index[key].add(record.record_id)

    if records_without_keys:
        warnings.append(
            f"Blocking: {len(records_without_keys)} records have no blocking keys "
            f"and may miss potential matches. IDs: {records_without_keys[:5]}..."
        )

    # Collect candidate pairs (deduplicated)
    candidate_set: Set[Tuple[str, str]] = set()

    for key, record_ids in block_index.items():
        record_list = list(record_ids)
        for i in range(len(record_list)):
            for j in range(i + 1, len(record_list)):
                # Normalize pair order for deduplication
                pair = tuple(sorted([record_list[i], record_list[j]]))
                candidate_set.add(pair)

    candidate_pairs = list(candidate_set)

    # Calculate reduction
    reduction_pct = (1 - len(candidate_pairs) / total_possible) * 100 if total_possible > 0 else 0

    if reduction_pct > 90:
        warnings.append(
            f"Blocking reduced comparisons by {reduction_pct:.1f}%. "
            f"This may miss some matches. Consider adding more blocking strategies."
        )

    return candidate_pairs, total_possible, warnings
