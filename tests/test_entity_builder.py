from app.core.entity_builder import build_entity
from app.models.schemas import Record, NormalizedRecord, MatchDecision, PairwiseMatch
from app.core.similarity import SimilarityScorer
from app.core.grouping import MatchGraph
from app.config.default import DEFAULT_CONFIG
from app.config.schemas import ThresholdConfig

def test_build_entity_happy_path():
    scorer = SimilarityScorer(DEFAULT_CONFIG)
    threshold_config = ThresholdConfig(
        high_confidence=0.85,
        low_confidence=0.6
    )

    # Raw records
    records = {
        "a": Record(
            id="a",
            text="One Dance",
            record_metadata={"artist": "Drake", "year": 2016},
            source_row=1
        ),
        "b": Record(
            id="b",
            text="One Dance Drake",
            record_metadata={"artist": "Drake"},
            source_row=2
        ),
        "c": Record(
            id="c",
            text="Drake - One Dance",
            record_metadata={"artist": "Drake"},
            source_row=3
        ),
    }

    # Normalized records
    normalized = {
        rid: NormalizedRecord(
            record_id=rid,
            tokens=["dance", "drake", "one"],
            normalized_text="one dance drake",
            original_record=rec
        )
        for rid, rec in records.items()
    }

    # Match graph with known matches
    graph = MatchGraph()
    for rid in records:
        graph.add_node(rid)

    graph.add_match(
        PairwiseMatch(
            record_a_id="a",
            record_b_id="b",
            final_score=0.95,
            signals={},
            signals_used=[],
            decision=MatchDecision.SAME_ENTITY,
            explanation="High confidence match"
        )
    )

    graph.add_match(
        PairwiseMatch(
            record_a_id="a",
            record_b_id="c",
            final_score=0.93,
            signals={},
            signals_used=[],
            decision=MatchDecision.SAME_ENTITY,
            explanation="High confidence match"
        )
    )

    # Build entity
    entity, is_flagged, warnings = build_entity(
        group={"a", "b", "c"},
        records=records,
        normalized_records=normalized,
        match_graph=graph,
        scorer=scorer,
        threshold_config=threshold_config
    )

    # Assertions - canonical must be one of the input records
    assert entity.canonical_name in {r.text for r in records.values()}
    assert set(entity.matched_record_ids) == {"a", "b", "c"}
    assert entity.confidence > 0.8
    assert not is_flagged
    assert "a" in entity.match_explanations
    assert "b" in entity.match_explanations
    assert "c" in entity.match_explanations
