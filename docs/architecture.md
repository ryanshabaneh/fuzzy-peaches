# Fuzzy Peaches: System Architecture

**Status:** Active Development
**Last Updated:** 2026-02-07

## TL;DR

Fuzzy Peaches is an entity resolution pipeline exposed via FastAPI. It ingests CSV/JSON records, normalizes text (lowercase, unicode, abbreviation expansion, sorted tokens), and optionally applies blocking to reduce the O(n^2) comparison space. Pairs are scored using four weighted signals (token Jaccard, edit distance, exact field match, length ratio) with automatic weight renormalization when signals are missing. Accepted matches form a graph whose connected components become entity groups. Each group is validated for transitive consistency, flagged if suspicious, and assigned a canonical representative scored on completeness, cleanliness, and centrality. Output includes full match explanations, per-stage timing, and a frozen config snapshot for reproducibility. The pipeline is fully functional; run persistence and retrieval endpoints are defined but not yet wired.

---

## 1. System Overview

Fuzzy Peaches is a configurable entity resolution system that identifies and groups duplicate records from structured data sources. Given a set of records (CSV or JSON), it normalizes text, generates candidate pairs, computes multi-signal similarity scores, and uses graph-based grouping to produce deduplicated entities with full explainability. The system prioritizes transparency over black-box accuracy: every match decision includes the contributing signals, every entity group is validated for internal consistency, and every canonical representative is selected via auditable scoring criteria.

```
                         Fuzzy Peaches Pipeline
                         ======================

  CSV/JSON ──> [ Ingest ] ──> [ Normalize ] ──> [ Block ] ──> [ Score ]
                                                                  |
                                                                  v
  Output  <── [ Canonical ] <── [ Validate ] <── [ Group ] <── [ Decide ]
    |
    v
  ResolutionResult
  ├── entities[]          (grouped, deduplicated records)
  ├── flagged_entity_ids  (inconsistent groups)
  ├── rejected_records    (singletons)
  ├── warnings[]          (non-fatal issues)
  └── stats{}             (timing, counts)
```

---

## 2. Pipeline Architecture (Current)

### Stage 1: Input Ingestion

Records are loaded from CSV or JSON files via format-specific loaders with a common interface.

- **Formats:** CSV (via `csv.DictReader`), JSON (array or newline-delimited)
- **Column mapping:** Caller-supplied mapping remaps source columns to internal fields (e.g., `{"text": "song_title", "artist": "performer"}`)
- **Auto-detection:** `LoaderFactory` selects the parser by file extension, falling back to content sniffing
- **Validation:** File size capped at 10MB; empty files and missing `text` fields rejected
- **Output:** `List[Record]` where each record has `id`, `text`, `record_metadata: Dict`, and `source_row`

```python
# Record schema
class Record(BaseModel):
    id: str
    text: str
    record_metadata: Dict[str, Any] = {}
    source_row: int
```

### Stage 2: Normalization

Each record's `text` field is transformed into a canonical form for comparison.

**Steps (in order):**
1. **Lowercase** the full string
2. **Abbreviation expansion** via regex word-boundary matching (`feat.` -> `featuring`, `&` -> `and`, `w/` -> `with`, `vs.` -> `versus`)
3. **Unicode NFD decomposition** followed by combining-mark removal (`cafe` <- `cafe`)
4. **Punctuation removal** (replace non-word/non-space characters with spaces)
5. **Whitespace collapse** and trim
6. **Tokenization:** split on whitespace, remove configurable stopwords, sort alphabetically

Alphabetical sorting makes token sets order-independent: `"Drake One Dance"` and `"One Dance Drake"` produce identical token lists `["dance", "drake", "one"]`.

```python
# Output
class NormalizedRecord(BaseModel):
    record_id: str
    tokens: List[str]          # sorted, stopword-filtered
    normalized_text: str       # cleaned string before tokenization
    original_record: Record    # preserved for metadata access
```

**Warnings emitted:** Records that normalize to empty token lists.

### Stage 3: Candidate Generation (Blocking)

Blocking reduces the comparison space from O(n^2) to O(n*k) by only comparing records that share a blocking key.

- **Toggle:** `blocking.enabled` (default: `false` -- all pairs compared)
- **Strategies (configurable, additive):**

| Strategy       | Key Format         | Example                     |
|---------------|--------------------|-----------------------------|
| `first_3_chars`| `f3:<prefix>`     | `f3:one` for "one dance"    |
| `first_token`  | `ft:<token>`      | `ft:dance` for ["dance", "one"] |
| `artist`       | `art:<artist>`    | `art:drake`                 |
| `year`         | `yr:<year>`       | `yr:2016`                   |

- **Inverted index:** `Dict[block_key, Set[record_id]]` -- pairs are generated within each bucket and deduplicated globally
- **Safety guard:** `min_key_length` (default: 3) prevents overly short keys from creating giant buckets

**Warnings emitted:**
- Records with no blocking keys (potential recall loss)
- Blocking reduction exceeding 90% of total pairs

### Stage 4: Pairwise Similarity Scoring

Each candidate pair is evaluated across four independent signals, combined via weighted sum with dynamic renormalization.

**Signals:**

| Signal              | Function               | Range  | Default Weight |
|---------------------|------------------------|--------|----------------|
| `token_jaccard`     | `\|A ∩ B\| / \|A ∪ B\|` | [0, 1] | 0.4            |
| `edit_distance`     | `rapidfuzz.fuzz.ratio / 100` | [0, 1] | 0.3        |
| `exact_field_match` | Case-insensitive equality on `artist` metadata | {0, 1} or `None` | 0.2 |
| `length_ratio`      | `min(len_a, len_b) / max(len_a, len_b)` | [0, 1] | 0.1 |

**Weight renormalization:** When a signal is not computable (e.g., `exact_field_match` returns `None` because one record lacks an `artist` field), it is excluded and the remaining weights are rescaled to sum to 1.0. This prevents records with missing metadata from being systematically penalized.

```python
# Example: both records have artist metadata
# Weights: 0.4 + 0.3 + 0.2 + 0.1 = 1.0 (no change)

# Example: record B has no artist
# exact_field_match returns None, excluded
# Renormalized: jaccard=0.4/0.8, edit=0.3/0.8, length=0.1/0.8
# Effective:    jaccard=0.50, edit=0.375, length=0.125 = 1.0
```

**Constraint:** Configured weights must sum to 1.0 (validated with 0.01 tolerance).

### Stage 5: Decision Logic

The final score is mapped to a three-tier decision using configurable thresholds.

| Decision          | Condition                                     | Default Range    |
|-------------------|-----------------------------------------------|------------------|
| `SAME_ENTITY`     | `score >= high_confidence`                    | [0.85, 1.0]      |
| `POSSIBLE_MATCH`  | `low_confidence <= score < high_confidence`   | [0.70, 0.85)     |
| `DIFFERENT`       | `score < low_confidence`                      | [0.0, 0.70)      |

Each decision includes a human-readable explanation citing the strongest and weakest contributing signals. Both `SAME_ENTITY` and `POSSIBLE_MATCH` pairs are added as edges to the match graph.

**Constraint:** `high_confidence >= low_confidence` (validated at config parse time).

### Stage 6: Graph Construction & Grouping

Accepted matches form an undirected graph where nodes are records and edges are `PairwiseMatch` objects (preserving full signal data for explainability). Entity groups are the connected components of this graph, found via BFS.

```
  MatchGraph
  ├── adjacency: Dict[str, Dict[str, PairwiseMatch]]  (bidirectional)
  └── nodes: Set[str]

  Connected components via BFS:
    A ── B ── C        D ── E        F
    └── component 1 ──┘    └── 2 ──┘  └── 3 (singleton)
```

Records with no accepted matches form singleton components.

### Stage 7: Consistency Validation

For each group of 3+ records, every internal pair is re-evaluated to detect transitive inconsistencies.

**Problem detected:**
```
  A ──(0.90)── B ──(0.86)── C
  A ──(0.55)── C  <-- below low_confidence threshold
```

Records A and C end up grouped via transitivity through B, but their direct similarity is low. The system flags the entity (adds its ID to `flagged_entity_ids`) and emits a warning rather than silently splitting the group.

Groups of 1-2 records are trivially consistent and skip validation.

### Stage 8: Canonical Selection

One record per group is selected as the canonical representative using a weighted multi-criteria score.

| Criterion       | Weight | Measures                                          |
|-----------------|--------|---------------------------------------------------|
| **Completeness** | 40%   | Fraction of non-null metadata fields              |
| **Cleanliness**  | 30%   | Average of: length penalty, special-char penalty, caps penalty |
| **Centrality**   | 30%   | Average pairwise similarity to all other group members |

The `selection_rationale` is included in the output so consumers can audit why a particular record was chosen.

### Stage 9: Output

The pipeline returns a `ResolutionResult` containing:

```python
class ResolutionResult(BaseModel):
    run_id: str                           # "run_<uuid_hex[:12]>"
    created_at: datetime
    entities: List[Entity]                # sorted by confidence descending
    rejected_records: List[str]           # singleton record IDs
    flagged_entity_ids: List[str]         # groups with consistency warnings
    warnings: List[str]                   # all non-fatal issues
    errors: List[str]                     # fatal issues (typically empty)
    stats: ResolutionStats                # counts + per-stage timing
    config_used: ResolverConfig           # frozen snapshot for reproducibility
```

Entity IDs are deterministic: `ENT_<sha256(canonical_name + sorted_record_ids)[:12]>`. Identical inputs with identical config produce identical outputs.

---

## 3. Key Design Decisions

### Why graph-based grouping instead of greedy matching?

Greedy matching (assigning each record to the first sufficiently similar match) creates order-dependent results and cannot represent multi-way relationships. Graph-based connected components naturally handle transitive matches: if A matches B and B matches C, all three are grouped regardless of whether A and C were directly compared. This is critical when blocking reduces the candidate space -- indirect connections through shared block keys still produce correct groupings.

### Why weighted heuristics instead of ML/embeddings?

Weighted heuristic scoring provides three properties that matter for an entity resolution tool:

1. **Interpretability.** Each match decision cites specific signal values and their weights. Users can understand *why* two records matched and adjust weights if the result is wrong.
2. **No training data required.** The system works out of the box on any dataset without labeled pairs.
3. **Debuggability.** When results are incorrect, the fix is a config change (adjust a weight or threshold), not a retraining cycle.

The trade-off is lower ceiling accuracy on complex domains where learned representations would outperform hand-crafted features.

### Why configurable thresholds?

Different datasets have different similarity distributions. Music metadata with standardized naming conventions needs higher thresholds than messy user-generated data. The three-tier decision model (`SAME_ENTITY` / `POSSIBLE_MATCH` / `DIFFERENT`) lets operators tune precision-recall trade-offs without code changes, and the `POSSIBLE_MATCH` band explicitly surfaces ambiguous cases for human review.

### Why validate transitive consistency?

Connected-component grouping trusts transitivity: if A-B and B-C match, A-C is grouped implicitly. But transitivity can produce false merges when B is a "bridge" record that is superficially similar to both A and C despite A and C being genuinely different entities. Re-evaluating all internal pairs and flagging groups with low-scoring pairs gives operators a targeted review list instead of requiring manual inspection of every group.

### Why renormalize weights when signals are missing?

Without renormalization, a record missing an `artist` field would effectively receive a 0.0 for the `exact_field_match` signal (20% of the total weight), systematically lowering its scores against all other records. This penalizes data incompleteness rather than actual dissimilarity. Renormalization redistributes the missing signal's weight proportionally across computable signals, ensuring that scores remain comparable regardless of metadata availability.

---

## 4. Complexity Analysis

### Time Complexity

| Stage                | Without Blocking | With Blocking     |
|----------------------|------------------|-------------------|
| Normalization        | O(n)             | O(n)              |
| Candidate generation | O(n^2)           | O(n * s)          |
| Pairwise comparison  | O(n^2 * f)       | O(k * f)          |
| Connected components | O(V + E)         | O(V + E)          |
| Consistency check    | O(g * m^2)       | O(g * m^2)        |
| Canonical selection  | O(g * m^2)       | O(g * m^2)        |

Where:
- **n** = total records
- **s** = number of blocking strategies
- **k** = candidate pairs after blocking (k << n^2 in practice)
- **f** = number of similarity signals (currently 4)
- **V** = nodes, **E** = edges in the match graph
- **g** = number of entity groups, **m** = max group size

The dominant cost is pairwise comparison. Without blocking, this is O(n^2). With blocking, it reduces to O(k) where k depends on the key distribution. In the worst case (one giant bucket), blocking degrades to O(n^2).

### Space Complexity

| Structure             | Size              | Lifetime    |
|-----------------------|-------------------|-------------|
| Normalized records    | O(n)              | Pipeline    |
| Block inverted index  | O(n * s)          | Ephemeral   |
| Candidate pairs list  | O(k)              | Ephemeral   |
| Match graph           | O(V + E)          | Pipeline    |
| Connected components  | O(V)              | Pipeline    |
| Output entities       | O(n)              | Returned    |

The match graph stores `PairwiseMatch` objects on edges (signals, explanation text), so edge weight is non-trivial. For a dataset of n records where ~p% of pairs match, the graph holds O(n + n^2 * p) data. This is manageable for datasets up to ~10K records but becomes a concern beyond that.

---

## 5. Scaling Roadmap (Planned)

The following improvements are not yet implemented.

### Full Run Persistence and Retrieval

SQLAlchemy ORM models (`ResolutionRunDB`, `RecordDB`, `EntityDB`) exist but the retrieval endpoints (`GET /runs/{run_id}`, `GET /runs`) are not wired to the database. Current state: `POST /resolve` runs the pipeline and returns results in the response body without persisting. Completing this would enable result auditing and comparison across runs.

### Parallel Pairwise Comparisons

The comparison loop in `_build_match_graph` is sequential. Since each pair is independent, this is trivially parallelizable with `concurrent.futures.ProcessPoolExecutor` or similar. The graph construction step would need to be synchronized but is cheap relative to scoring.

### Approximate Nearest Neighbor (ANN) for Candidate Generation

Replace or supplement blocking with ANN indices (e.g., FAISS, Annoy) over TF-IDF or character n-gram vectors. This would provide better recall than prefix-based blocking while maintaining sub-quadratic candidate generation, particularly for datasets where blocking keys have poor discriminative power.

### Incremental Resolution for Streaming Data

Support resolving new records against an existing entity set without re-running the full pipeline. This requires persisting the match graph and normalized records, and defining merge semantics for when a new record bridges two previously separate entities.

### PostgreSQL for Production

The current SQLite backend (`sqlite:///./entity_resolver.db`) is suitable for development. A production deployment would use PostgreSQL with JSONB columns for metadata and signal storage, connection pooling, and proper migration tooling.

---

## 6. Observability (Current)

### Run Tracking

Every resolution invocation generates a unique `run_id` (`run_<uuid_hex[:12]>`) and freezes the active config into `config_used` for reproducibility. The same input + same config produces the same entity IDs (deterministic via SHA-256).

### Stage Timings

Wall-clock timing is captured per pipeline phase:

```json
{
  "timing_ms": {
    "normalization_ms": 2.5,
    "blocking_ms": 0.8,
    "comparison_ms": 45.2,
    "grouping_ms": 0.3,
    "entity_building_ms": 1.2
  }
}
```

### Warnings

Non-fatal issues are surfaced in the `warnings` array:

| Warning Category        | Trigger                                              |
|-------------------------|------------------------------------------------------|
| Empty normalization     | Record produces zero tokens after normalization      |
| Missing blocking keys   | Record has no blocking keys (potential recall loss)   |
| Excessive blocking      | Blocking reduction >90% of total comparisons         |
| Transitive inconsistency| Grouped records have direct similarity below `low_confidence` |

### Flagged Entities

Entity IDs with consistency validation failures are collected in `flagged_entity_ids`, giving operators a targeted review list without requiring full result inspection.

### Stats

```python
class ResolutionStats(BaseModel):
    total_records: int
    total_entities: int
    total_comparisons: int
    comparisons_skipped_by_blocking: int
    matches_accepted: int                  # SAME_ENTITY + POSSIBLE_MATCH
    matches_rejected: int                  # DIFFERENT
    matches_flagged: int                   # entities with consistency issues
    timing_ms: Dict[str, float]
```

---

## 7. API Reference (Current)

**Base URL:** FastAPI application (default `http://localhost:8000`)

| Endpoint                          | Method | Status            | Description                        |
|-----------------------------------|--------|-------------------|------------------------------------|
| `/health`                         | GET    | Implemented       | Returns `{"status": "healthy", "version": "1.0.0"}` |
| `/config/default`                 | GET    | Implemented       | Returns default `ResolverConfig`   |
| `/resolve`                        | POST   | Implemented       | Upload file, run entity resolution |
| `/runs/{run_id}`                  | GET    | Planned           | Retrieve previous resolution run   |
| `/runs`                           | GET    | Planned           | List all resolution runs           |
| `/entities/{run_id}/{entity_id}`  | GET    | Planned           | Retrieve single entity details     |

### POST /resolve

**Request:** `multipart/form-data`

| Field                | Type           | Required | Description                              |
|----------------------|----------------|----------|------------------------------------------|
| `file`               | `UploadFile`   | Yes      | CSV or JSON file (max 10MB)              |
| `config_json`        | `string`       | No       | `ResolverConfig` serialized as JSON      |
| `column_mapping_json`| `string`       | No       | Field remapping, e.g. `{"text": "title"}`|

**Response:** `ResolutionResult` (see Stage 9 above)

**Error responses:**

| Status | Condition                              |
|--------|----------------------------------------|
| 400    | File too large, invalid config JSON, invalid column mapping, validation failure, no valid records |

### GET /config/default

Returns the full default configuration including weights, thresholds, blocking settings, and stopwords. Useful for UI pre-population.

```json
{
  "weights": {
    "token_jaccard": 0.4,
    "edit_distance": 0.3,
    "exact_field_match": 0.2,
    "length_ratio": 0.1
  },
  "thresholds": {
    "high_confidence": 0.85,
    "low_confidence": 0.70
  },
  "blocking": {
    "enabled": false,
    "strategies": ["first_3_chars", "artist"],
    "min_key_length": 3
  },
  "stopwords": ["feat", "featuring", "ft", "radio", "edit", "remaster", "..."]
}
```