from typing import Dict, Set, Tuple, List
from app.models.schemas import Entity, Record, NormalizedRecord
from app.core.similarity import SimilarityScorer
from app.core.grouping import MatchGraph, validate_group_consistency
from app.core.canonical import select_canonical
from app.config.schemas import ThresholdConfig

def build_entity(
    group: Set[str],
    records: Dict[str, Record],
    normalized_records: Dict[str, NormalizedRecord],
    match_graph: MatchGraph,
    scorer: SimilarityScorer,
    threshold_config: ThresholdConfig
) -> Tuple[Entity, bool, List[str]]:
    """
    Build complete Entity from a group of record IDs.

    Returns:
        (entity, is_flagged, warnings)
    """
    warnings = []

    # Select canonical
    canonical_id, selection_scores = select_canonical(
        group, records, normalized_records, scorer
    )
    canonical_record = records[canonical_id]

    # Validate consistency
    is_consistent, min_score, consistency_warnings = validate_group_consistency(
        group, normalized_records, scorer, threshold_config
    )
    warnings.extend(consistency_warnings)
    is_flagged = not is_consistent

    # Compute group confidence (average pairwise similarity)
    if len(group) == 1:
        confidence = 1.0
    else:
        total_score = 0.0
        pair_count = 0
        group_list = list(group)
        for i in range(len(group_list)):
            for j in range(i + 1, len(group_list)):
                score, _, _ = scorer.compute(
                    normalized_records[group_list[i]],
                    normalized_records[group_list[j]]
                )
                total_score += score
                pair_count += 1
        confidence = total_score / pair_count if pair_count > 0 else 1.0

    # Build match explanations
    match_explanations = {}
    for record_id in group:
        if record_id == canonical_id:
            match_explanations[record_id] = "Selected as canonical representative"
        else:
            match = match_graph.get_match(canonical_id, record_id)
            if match:
                match_explanations[record_id] = match.explanation
            else:
                # Indirect match (through transitivity)
                match_explanations[record_id] = (
                    f"Matched via transitivity (not directly compared to canonical)"
                )

    # Generate deterministic ID
    entity_id = Entity.generate_id(canonical_record.text, list(group))

    entity = Entity(
        id=entity_id,
        canonical_name=canonical_record.text,
        canonical_metadata=canonical_record.record_metadata,
        confidence=confidence,
        matched_record_ids=list(group),
        match_explanations=match_explanations,
        selection_rationale=selection_scores
    )

    return entity, is_flagged, warnings
