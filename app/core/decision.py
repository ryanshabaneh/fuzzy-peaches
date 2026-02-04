from typing import Dict, Tuple
from app.models.schemas import MatchDecision, PairwiseMatch
from app.config.schemas import ThresholdConfig

def decide_match(
    score: float,
    signals: Dict[str, float],
    signals_used: list,
    record_a_id: str,
    record_b_id: str,
    config: ThresholdConfig
) -> PairwiseMatch:
    """
    Make match decision with human-readable explanation.
    """
    # Find strongest and weakest signals (only from those used)
    used_signals = {k: v for k, v in signals.items() if k in signals_used and v is not None}

    if used_signals:
        strongest = max(used_signals.items(), key=lambda x: x[1])
        weakest = min(used_signals.items(), key=lambda x: x[1])
    else:
        strongest = ("none", 0)
        weakest = ("none", 0)

    # Decision logic
    if score >= config.high_confidence:
        decision = MatchDecision.SAME_ENTITY
        explanation = (
            f"High confidence match (score={score:.3f} >= {config.high_confidence}). "
            f"Strongest signal: {strongest[0]} ({strongest[1]:.3f})."
        )
    elif score >= config.low_confidence:
        decision = MatchDecision.POSSIBLE_MATCH
        explanation = (
            f"Possible match ({config.low_confidence} <= score={score:.3f} < {config.high_confidence}). "
            f"Strongest: {strongest[0]} ({strongest[1]:.3f}), "
            f"Weakest: {weakest[0]} ({weakest[1]:.3f}). "
            f"Manual review recommended."
        )
    else:
        decision = MatchDecision.DIFFERENT
        explanation = (
            f"No match (score={score:.3f} < {config.low_confidence}). "
            f"Weakest signal: {weakest[0]} ({weakest[1]:.3f})."
        )

    return PairwiseMatch(
        record_a_id=record_a_id,
        record_b_id=record_b_id,
        final_score=score,
        signals=signals,
        signals_used=signals_used,
        decision=decision,
        explanation=explanation
    )
