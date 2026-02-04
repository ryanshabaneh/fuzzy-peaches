from typing import Dict, List, Set, Tuple
from collections import defaultdict
from app.models.schemas import PairwiseMatch, NormalizedRecord
from app.core.similarity import SimilarityScorer
from app.config.schemas import ThresholdConfig

class MatchGraph:
    """
    Graph where nodes are record IDs and edges are matches.
    Stores full PairwiseMatch objects as edge data for explainability.
    """

    def __init__(self):
        # adjacency[node_a][node_b] = PairwiseMatch
        self.adjacency: Dict[str, Dict[str, PairwiseMatch]] = defaultdict(dict)
        self._nodes: Set[str] = set()

    def add_node(self, record_id: str):
        self._nodes.add(record_id)

    def add_match(self, match: PairwiseMatch):
        """Add bidirectional edge."""
        self._nodes.add(match.record_a_id)
        self._nodes.add(match.record_b_id)
        self.adjacency[match.record_a_id][match.record_b_id] = match
        self.adjacency[match.record_b_id][match.record_a_id] = match

    def get_neighbors(self, record_id: str) -> List[Tuple[str, PairwiseMatch]]:
        """Get all connected records with match details."""
        return list(self.adjacency[record_id].items())

    def get_match(self, id_a: str, id_b: str) -> PairwiseMatch:
        """Get match between two specific records."""
        return self.adjacency.get(id_a, {}).get(id_b)

    @property
    def nodes(self) -> Set[str]:
        return self._nodes

    def __repr__(self):
        edge_count = sum(len(neighbors) for neighbors in self.adjacency.values()) // 2
        return f"MatchGraph(nodes={len(self._nodes)}, edges={edge_count})"


def find_connected_components(graph: MatchGraph) -> List[Set[str]]:
    """
    Find all connected components using BFS.
    Each component represents one entity.
    """
    visited = set()
    components = []

    for node in graph.nodes:
        if node in visited:
            continue

        # BFS from this node
        component = set()
        queue = [node]

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue

            visited.add(current)
            component.add(current)

            for neighbor_id, _ in graph.get_neighbors(current):
                if neighbor_id not in visited:
                    queue.append(neighbor_id)

        components.append(component)

    return components


def validate_group_consistency(
    group: Set[str],
    normalized_records: Dict[str, NormalizedRecord],
    scorer: SimilarityScorer,
    threshold_config: ThresholdConfig
) -> Tuple[bool, float, List[str]]:
    """
    Validate that all pairs within a group have acceptable similarity.

    This catches transitive closure errors:
    - A matches B (0.90)
    - B matches C (0.86)
    - But A-C might only score 0.60

    Returns:
        (is_consistent, min_internal_score, warnings)
    """
    if len(group) <= 2:
        return True, 1.0, []

    warnings = []
    min_score = 1.0
    group_list = list(group)

    for i in range(len(group_list)):
        for j in range(i + 1, len(group_list)):
            id_a, id_b = group_list[i], group_list[j]
            record_a = normalized_records.get(id_a)
            record_b = normalized_records.get(id_b)

            if not record_a or not record_b:
                continue

            score, _, _ = scorer.compute(record_a, record_b)
            min_score = min(min_score, score)

            if score < threshold_config.low_confidence:
                warnings.append(
                    f"Transitive closure warning: {id_a} and {id_b} "
                    f"have low direct similarity ({score:.3f}) despite being grouped."
                )

    is_consistent = len(warnings) == 0
    return is_consistent, min_score, warnings
