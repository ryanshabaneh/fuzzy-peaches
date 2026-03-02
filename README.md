# Fuzzy Entity Resolver

A full-stack system for identifying and grouping inconsistent records in messy datasets.

## Problem Statement

Given inconsistent data, identify which records refer to the same entity:

```
Input:
- "One Dance - Drake"
- "Drake – One Dance (feat. Wizkid)"
- "ONE DANCE (Radio Edit)"

Output:
- Entity: "One Dance" by Drake
- Confidence: 92%
- Matched records: [all three above]
```

## Resolution Pipeline

Records are normalized and compared using multiple similarity signals.
Pairwise similarities are converted into confidence bands and grouped
using a graph-based approach with consistency validation.
Each resulting group is assigned a canonical representative based on
completeness, cleanliness, and centrality.

## Similarity Signals

| Signal | Weight | Description |
|--------|--------|-------------|
| Token Jaccard | 40% | Set overlap of normalized tokens |
| Edit Distance | 30% | Character-level similarity (rapidfuzz) |
| Exact Field Match | 20% | Exact match on artist/metadata |
| Length Ratio | 10% | Similar length indicates similar content |

Weights are renormalized when signals are missing (e.g., no artist field).

## Installation

```bash
# Backend
pip install -r requirements.txt
python main.py

# Frontend
cd frontend
npm install
npm run dev
```

## API & Configuration

The resolver exposes a minimal HTTP API for running entity resolution jobs
and previewing configuration.

- `POST /resolve` — upload a CSV or JSON file and run resolution  
- `GET /config/default` — fetch default resolver settings  
- `GET /health` — service health check  

Demo hardening:
- CORS is restricted to `http://localhost:5173` and `https://fuzzy-peaches.vercel.app`.
- `POST /resolve` rejects files over 5MB and payloads with more than 20,000 parsed records.
- `POST /resolve` has an in-memory best-effort rate limit of 10 requests per 60s per client IP (supports `X-Forwarded-For`).

All matching behavior (weights, thresholds, blocking strategies) is fully
configuration-driven and adjustable without code changes.

## Design Decisions

- **Heuristics over ML** — prioritizes interpretability, debuggability, and zero training data
- **Graph-based grouping** — naturally handles transitive matches and enables consistency validation
- **Weight renormalization** — avoids penalizing records with missing or incomplete fields

## Known Limitations

- Limited semantic understanding (e.g., synonyms)
- Some company-name variants (e.g., "Apple Inc." vs "Apple Incorporated") may
  fall into the borderline/review band depending on thresholds and normalization,
  since legal suffixes are handled differently (e.g., "inc" may be stripped while
  "incorporated" remains). This is expected heuristic behavior and can be tuned
  via thresholds or by extending the stopword list (e.g., adding "incorporated").
- Blocking strategies trade recall for performance
- Some transitive groups may contain borderline pairs (explicitly flagged)
- No incremental updates; resolution runs are batch-based
- Practical scale ~100k records without distributed processing

## Benchmarks

Synthetic dataset with 30% duplicates, measured on Apple Silicon (M-series):

| Records | Blocking | Time (s) | Entities | Comparisons | Skipped |
|---------|----------|----------|----------|-------------|---------|
| 100     | OFF      | 0.03     | 67       | 4,950       | 0       |
| 100     | ON       | <0.01    | 67       | 374         | 4,576   |
| 1,000   | OFF      | 2.77     | 446      | 499,500     | 0       |
| 1,000   | ON       | 0.23     | 446      | 31,952      | 467,548 |
| 10,000  | OFF      | 299.04   | 951      | 49,995,000  | 0       |
| 10,000  | ON       | 23.62    | 951      | 3,172,987   | 46,822,013 |

Blocking uses `first_3_chars` + `artist` keys to generate candidate pairs. On this synthetic dataset (30% duplicates), blocking removes ~93% of pair comparisons with no change in entity count. Run `make bench` to reproduce.

## Testing

```bash
make test
```

## Project Structure

```
fuzzy-peaches/
├── app/
│   ├── api/
│   │   └── routes.py          # FastAPI endpoints
│   ├── config/
│   │   ├── schemas.py         # Pydantic config models
│   │   └── default.py         # Default configuration
│   ├── core/
│   │   ├── normalizer.py      # Text normalization
│   │   ├── similarity.py      # Similarity scoring
│   │   ├── decision.py        # Match decision logic
│   │   ├── grouping.py        # Graph-based grouping
│   │   ├── blocking.py        # Candidate pair reduction
│   │   ├── canonical.py       # Canonical selection
│   │   ├── entity_builder.py  # Entity construction
│   │   └── pipeline.py        # Main resolution pipeline
│   ├── loaders/
│   │   ├── base.py            # Abstract loader
│   │   ├── csv_loader.py      # CSV file loader
│   │   ├── json_loader.py     # JSON file loader
│   │   └── factory.py         # Loader factory
│   └── models/
│       ├── schemas.py         # Pydantic data models
│       ├── db_models.py       # SQLAlchemy models
│       └── database.py        # Database utilities
├── frontend/
│   └── src/
│       ├── api/
│       │   └── resolver.js    # API client
│       └── components/
│           ├── FileUpload.jsx
│           ├── ResultsTable.jsx
│           └── EntityDetail.jsx
├── tests/
│   ├── conftest.py
│   ├── test_api.py
│   ├── test_pipeline.py
│   ├── test_similarity.py
│   ├── test_normalizer.py
│   └── test_entity_builder.py
├── main.py
└── requirements.txt
```

## License

MIT
