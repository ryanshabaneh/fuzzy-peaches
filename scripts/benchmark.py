"""
Benchmark script for Fuzzy Peaches entity resolution pipeline.

Generates synthetic song records with controlled duplicates,
runs resolution with blocking ON and OFF, and prints a comparison table.

Usage: python scripts/benchmark.py
"""

import sys
import os
import time
import random
import platform

# Allow imports from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.schemas import Record
from app.config.schemas import ResolverConfig, BlockingConfig
from app.config.default import DEFAULT_STOPWORDS
from app.core.pipeline import EntityPipeline

# Seed for reproducible benchmarks
random.seed(42)

TITLES = [
    "One Dance", "Hotline Bling", "Shake It Off", "Blinding Lights",
    "Bohemian Rhapsody", "Stairway to Heaven", "Hotel California",
    "Smells Like Teen Spirit", "Imagine", "Yesterday", "Hey Jude",
    "Let It Be", "Come Together", "Purple Rain", "Billie Jean",
    "Thriller", "Like a Prayer", "Sweet Child O Mine", "November Rain",
    "Wonderwall", "Creep", "Karma Police", "No Surprises",
    "Bitter Sweet Symphony", "Lose Yourself", "Stan", "Without Me",
    "Humble", "Alright", "DNA", "Money Trees", "Swimming Pools",
    "Runaway", "Stronger", "Gold Digger", "All of the Lights",
    "Rolling in the Deep", "Someone Like You", "Hello", "Skyfall",
    "Halo", "Crazy in Love", "Single Ladies", "Formation",
    "Bad Guy", "Lovely", "Ocean Eyes", "Happier Than Ever",
    "Levitating", "Dont Start Now", "Physical", "Break My Heart",
]

ARTISTS = [
    "Drake", "Taylor Swift", "The Weeknd", "Queen", "Led Zeppelin",
    "Eagles", "Nirvana", "John Lennon", "The Beatles", "Prince",
    "Michael Jackson", "Madonna", "Guns N Roses", "Oasis",
    "Radiohead", "The Verve", "Eminem", "Kendrick Lamar",
    "Kanye West", "Adele", "Beyonce", "Billie Eilish", "Dua Lipa",
]

VARIATIONS = [
    lambda t, a: f"{t} - {a}",
    lambda t, a: f"{t.upper()} - {a}",
    lambda t, a: f"{t.lower()} - {a}",
    lambda t, a: f"{t} (Remix) - {a}",
    lambda t, a: f"{t} (Radio Edit) - {a}",
    lambda t, a: f"{t} (Remastered) - {a}",
    lambda t, a: f"{t} (Live) - {a}",
    lambda t, a: f"{t} feat. {a}",
    lambda t, a: f"{t} ft. {a}",
]


def generate_test_data(n_records, duplicate_ratio=0.3):
    """Generate synthetic song records with controlled duplicate ratio."""
    records = []
    n_unique = int(n_records * (1 - duplicate_ratio))
    n_duplicates = n_records - n_unique

    # Generate unique records
    for i in range(n_unique):
        title = random.choice(TITLES)
        artist = random.choice(ARTISTS)
        text = f"{title} - {artist}"
        records.append(Record(
            id=str(i + 1),
            text=text,
            record_metadata={"artist": artist},
            source_row=i + 1,
        ))

    # Generate duplicates (variations of existing records)
    for i in range(n_duplicates):
        source = random.choice(records[:n_unique])
        title_part = source.text.split(" - ")[0]
        artist = source.record_metadata.get("artist", "Unknown")
        variation = random.choice(VARIATIONS)
        text = variation(title_part, artist)
        records.append(Record(
            id=str(n_unique + i + 1),
            text=text,
            record_metadata={"artist": artist},
            source_row=n_unique + i + 1,
        ))

    random.shuffle(records)
    return records


def make_config(blocking_enabled):
    """Create a resolver config with blocking toggled."""
    return ResolverConfig(
        blocking=BlockingConfig(
            enabled=blocking_enabled,
            strategies=["first_3_chars", "artist"],
        ),
        stopwords=DEFAULT_STOPWORDS,
    )


def run_benchmark(n_records, blocking_enabled, records):
    """Run pipeline and return stats."""
    config = make_config(blocking_enabled)
    pipeline = EntityPipeline(config)

    start = time.perf_counter()
    result = pipeline.resolve(records)
    elapsed = time.perf_counter() - start

    return {
        "records": n_records,
        "blocking": "ON" if blocking_enabled else "OFF",
        "time_s": elapsed,
        "entities": result.stats.total_entities,
        "comparisons": result.stats.total_comparisons,
        "skipped": result.stats.comparisons_skipped_by_blocking,
    }


def format_number(n):
    """Format integer with commas."""
    return f"{n:,}"


def main():
    sizes = [100, 500, 1_000, 5_000, 10_000]
    results = []

    print("Fuzzy Peaches Benchmark")
    print("=" * 50)
    print()

    for size in sizes:
        print(f"Generating {format_number(size)} records...")
        records = generate_test_data(size)

        for blocking in [False, True]:
            label = "ON" if blocking else "OFF"
            print(f"  Running with blocking {label}...", end="", flush=True)
            row = run_benchmark(size, blocking, records)
            print(f" {row['time_s']:.2f}s")
            results.append(row)

        print()

    # Print markdown table
    print()
    print("## Results")
    print()
    print("| Records | Blocking | Time (s) | Entities | Comparisons | Skipped |")
    print("|---------|----------|----------|----------|-------------|---------|")

    for r in results:
        print(
            f"| {format_number(r['records']):>7} "
            f"| {r['blocking']:<8} "
            f"| {r['time_s']:>8.2f} "
            f"| {format_number(r['entities']):>8} "
            f"| {format_number(r['comparisons']):>11} "
            f"| {format_number(r['skipped']):>7} |"
        )

    # Machine info
    print()
    print("## Environment")
    print()
    print(f"- Python: {sys.version.split()[0]}")
    print(f"- Platform: {platform.platform()}")
    print(f"- CPU: {platform.processor() or 'unknown'}")


if __name__ == "__main__":
    main()
