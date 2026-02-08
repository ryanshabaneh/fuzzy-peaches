import logging
logger = logging.getLogger(__name__)
import time
import uuid
from typing import List, Dict, Tuple
from copy import deepcopy

from app.models.schemas import (
    Record, NormalizedRecord, Entity, ResolutionResult,
    ResolutionStats, MatchDecision
)
from app.config.schemas import ResolverConfig
from app.core.normalizer import Normalizer
from app.core.similarity import SimilarityScorer
from app.core.decision import decide_match
from app.core.grouping import MatchGraph, find_connected_components
from app.core.blocking import get_candidate_pairs
from app.core.entity_builder import build_entity

logger = logging.getLogger(__name__)


class EntityPipeline:
    """
    Main resolution pipeline.

    Architecture:
    1. Normalize all records
    2. Generate candidate pairs (with optional blocking)
    3. Compare pairs and build match graph
    4. Find connected components (entity groups)
    5. Build entities with canonical selection
    6. Return results with full observability
    """

    def __init__(self, config: ResolverConfig):
        self.config = config
        self.normalizer = Normalizer(config)
        self.scorer = SimilarityScorer(config)

    def resolve(self, records: List[Record]) -> ResolutionResult:
        """Run full resolution pipeline."""
        logger.info("Starting resolution | records=%d", len(records))
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        timing = {}
        warnings = []
        errors = []

        # Freeze config to ensure immutability
        config_used = self.config.frozen_copy()

        # Phase 1: Normalize
        start = time.perf_counter()
        normalized_records, norm_warnings = self._normalize_all(records)
        timing['normalization_ms'] = (time.perf_counter() - start) * 1000
        warnings.extend(norm_warnings)

        # Phase 2: Generate candidate pairs
        start = time.perf_counter()
        candidate_pairs, total_possible, block_warnings = get_candidate_pairs(
            list(normalized_records.values()),
            self.config.blocking
        )
        timing['blocking_ms'] = (time.perf_counter() - start) * 1000
        warnings.extend(block_warnings)

        comparisons_skipped = total_possible - len(candidate_pairs)

        # Phase 3: Compare pairs and build graph
        start = time.perf_counter()
        graph, match_stats = self._build_match_graph(
            normalized_records,
            candidate_pairs
        )
        timing['comparison_ms'] = (time.perf_counter() - start) * 1000

        # Phase 4: Find connected components
        start = time.perf_counter()
        components = find_connected_components(graph)
        timing['grouping_ms'] = (time.perf_counter() - start) * 1000

        # Phase 5: Build entities
        start = time.perf_counter()
        records_dict = {r.id: r for r in records}
        entities, flagged_ids, entity_warnings = self._build_entities(
            components, records_dict, normalized_records, graph
        )
        timing['entity_building_ms'] = (time.perf_counter() - start) * 1000
        warnings.extend(entity_warnings)

        # Identify rejected records (single-record entities below confidence)
        rejected = [
            e.matched_record_ids[0]
            for e in entities
            if len(e.matched_record_ids) == 1
        ]

        # Build stats
        stats = ResolutionStats(
            total_records=len(records),
            total_entities=len(entities),
            total_comparisons=len(candidate_pairs),
            comparisons_skipped_by_blocking=comparisons_skipped,
            matches_accepted=match_stats['accepted'],
            matches_rejected=match_stats['rejected'],
            matches_flagged=len(flagged_ids),
            timing_ms=timing
        )

        result = ResolutionResult(
            run_id=run_id,
            entities=entities,
            rejected_records=rejected,
            flagged_entity_ids=flagged_ids,
            warnings=warnings,
            errors=errors,
            stats=stats,
            config_used=config_used
        )

        logger.info(
            "Resolution complete | run_id=%s | records=%d | entities=%d | flagged=%d | timing_ms=%s",
            result.run_id,
            len(records),
            len(result.entities),
            len(result.flagged_entity_ids),
            result.stats.timing_ms,
        )

        return result

    def _normalize_all(
        self,
        records: List[Record]
    ) -> Tuple[Dict[str, NormalizedRecord], List[str]]:
        """Normalize all records, collecting warnings."""
        normalized = {}
        warnings = []

        for record in records:
            norm = self.normalizer.normalize_record(record)

            if not norm.tokens:
                warnings.append(
                    f"Record {record.id}: Normalized to empty tokens. "
                    f"Original: '{record.text[:50]}...'"
                )

            normalized[record.id] = norm

        return normalized, warnings

    def _build_match_graph(
        self,
        normalized_records: Dict[str, NormalizedRecord],
        candidate_pairs: List[Tuple[str, str]]
    ) -> Tuple[MatchGraph, Dict[str, int]]:
        """Compare candidate pairs and build match graph."""
        graph = MatchGraph()
        stats = {'accepted': 0, 'rejected': 0}

        # Add all records as nodes
        for record_id in normalized_records:
            graph.add_node(record_id)

        # Compare pairs
        for id_a, id_b in candidate_pairs:
            record_a = normalized_records[id_a]
            record_b = normalized_records[id_b]

            score, signals, signals_used = self.scorer.compute(record_a, record_b)

            match = decide_match(
                score, signals, signals_used,
                id_a, id_b,
                self.config.thresholds
            )

            if match.decision in [MatchDecision.SAME_ENTITY, MatchDecision.POSSIBLE_MATCH]:
                graph.add_match(match)
                stats['accepted'] += 1
            else:
                stats['rejected'] += 1

        return graph, stats

    def _build_entities(
        self,
        components: List[set],
        records: Dict[str, Record],
        normalized_records: Dict[str, NormalizedRecord],
        graph: MatchGraph
    ) -> Tuple[List[Entity], List[str], List[str]]:
        """Build entities from connected components."""
        entities = []
        flagged_ids = []
        warnings = []

        for component in components:
            entity, is_flagged, entity_warnings = build_entity(
                component,
                records,
                normalized_records,
                graph,
                self.scorer,
                self.config.thresholds
            )

            entities.append(entity)
            warnings.extend(entity_warnings)

            if is_flagged:
                flagged_ids.append(entity.id)

        # Sort by confidence descending
        entities.sort(key=lambda e: e.confidence, reverse=True)

        return entities, flagged_ids, warnings
