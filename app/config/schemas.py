from pydantic import BaseModel, Field, model_validator
from typing import List
from copy import deepcopy

class SimilarityWeights(BaseModel):
    token_jaccard: float = 0.4
    edit_distance: float = 0.3
    exact_field_match: float = 0.2
    length_ratio: float = 0.1

    @model_validator(mode='after')
    def weights_must_sum_to_one(self) -> 'SimilarityWeights':
        total = (
            self.token_jaccard +
            self.edit_distance +
            self.exact_field_match +
            self.length_ratio
        )
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total}")
        return self

class ThresholdConfig(BaseModel):
    high_confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    low_confidence: float = Field(default=0.70, ge=0.0, le=1.0)

    @model_validator(mode='after')
    def high_must_exceed_low(self) -> 'ThresholdConfig':
        if self.high_confidence < self.low_confidence:
            raise ValueError("high_confidence must be >= low_confidence")
        return self

class BlockingConfig(BaseModel):
    enabled: bool = False
    strategies: List[str] = Field(default_factory=lambda: ["first_3_chars", "artist"])
    min_key_length: int = 3  # Minimum chars required to generate blocking key

class ResolverConfig(BaseModel):
    weights: SimilarityWeights = Field(default_factory=SimilarityWeights)
    thresholds: ThresholdConfig = Field(default_factory=ThresholdConfig)
    blocking: BlockingConfig = Field(default_factory=BlockingConfig)
    stopwords: List[str] = Field(default_factory=list)

    def frozen_copy(self) -> 'ResolverConfig':
        """Return an immutable deep copy for storing with results."""
        return ResolverConfig.model_validate(deepcopy(self.model_dump()))
