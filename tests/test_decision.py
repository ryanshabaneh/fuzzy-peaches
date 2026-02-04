from app.core.decision import decide_match
from app.models.schemas import MatchDecision
from app.config.schemas import ThresholdConfig

def make_config():
    return ThresholdConfig(
        high_confidence=0.85,
        low_confidence=0.6
    )

def test_high_confidence_match():
    config = make_config()

    result = decide_match(
        score=0.92,
        signals={
            "token_jaccard": 0.9,
            "edit_distance": 0.88
        },
        signals_used=["token_jaccard", "edit_distance"],
        record_a_id="a",
        record_b_id="b",
        config=config
    )

    assert result.decision == MatchDecision.SAME_ENTITY
    assert "High confidence" in result.explanation


def test_possible_match():
    config = make_config()

    result = decide_match(
        score=0.7,
        signals={
            "token_jaccard": 0.75,
            "edit_distance": 0.65
        },
        signals_used=["token_jaccard", "edit_distance"],
        record_a_id="a",
        record_b_id="b",
        config=config
    )

    assert result.decision == MatchDecision.POSSIBLE_MATCH
    assert "Possible match" in result.explanation


def test_no_match():
    config = make_config()

    result = decide_match(
        score=0.3,
        signals={
            "token_jaccard": 0.2,
            "edit_distance": 0.25
        },
        signals_used=["token_jaccard", "edit_distance"],
        record_a_id="a",
        record_b_id="b",
        config=config
    )

    assert result.decision == MatchDecision.DIFFERENT
    assert "No match" in result.explanation