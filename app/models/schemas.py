from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from enum import Enum
from datetime import datetime
import hashlib

class Record(BaseModel):
    id: str
    text: str
    record_metadata: Dict[str, Any] = Field(default_factory=dict)  # Avoid 'metadata' name
    source_row: int

class NormalizedRecord(BaseModel):
    record_id: str
    tokens: List[str] = Field(default_factory=list)
    normalized_text: str
    original_record: Record

class MatchDecision(str, Enum):
    SAME_ENTITY = "same_entity"
    POSSIBLE_MATCH = "possible_match"
    DIFFERENT = "different"

class PairwiseMatch(BaseModel):
    record_a_id: str
    record_b_id: str
    final_score: float
    signals: Dict[str, float] = Field(default_factory=dict)
    signals_used: List[str] = Field(default_factory=list)  # Which signals were computable
    decision: MatchDecision
    explanation: str

class Entity(BaseModel):
    id: str
    canonical_name: str
    canonical_metadata: Dict[str, Any] = Field(default_factory=dict)
    confidence: float
    matched_record_ids: List[str] = Field(default_factory=list)
    match_explanations: Dict[str, str] = Field(default_factory=dict)
    selection_rationale: Dict[str, float] = Field(default_factory=dict)  # Why this canonical was chosen

    @staticmethod
    def generate_id(canonical_name: str, record_ids: List[str]) -> str:
        """Generate deterministic entity ID for reproducibility."""
        sorted_ids = sorted(record_ids)
        content = f"{canonical_name}|{'|'.join(sorted_ids)}"
        return f"ENT_{hashlib.sha256(content.encode()).hexdigest()[:12]}"

class ResolutionStats(BaseModel):
    total_records: int
    total_entities: int
    total_comparisons: int
    comparisons_skipped_by_blocking: int = 0
    matches_accepted: int
    matches_rejected: int
    matches_flagged: int = 0
    timing_ms: Dict[str, float] = Field(default_factory=dict)

class ResolutionResult(BaseModel):
    run_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    entities: List[Entity] = Field(default_factory=list)
    rejected_records: List[str] = Field(default_factory=list)
    flagged_entity_ids: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    stats: ResolutionStats
    config_used: 'ResolverConfig'  # Forward reference

# Import at end to avoid circular import
from app.config.schemas import ResolverConfig
ResolutionResult.model_rebuild()
