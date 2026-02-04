from app.config.schemas import ResolverConfig, SimilarityWeights, ThresholdConfig, BlockingConfig

DEFAULT_STOPWORDS = [
    "feat", "featuring", "ft", "radio", "edit", "remaster",
    "remastered", "remix", "remixed", "live", "acoustic",
    "version", "original", "mix", "inc", "ltd", "llc",
    "corp", "corporation", "company", "the"
]

DEFAULT_CONFIG = ResolverConfig(
    weights=SimilarityWeights(),
    thresholds=ThresholdConfig(),
    blocking=BlockingConfig(),
    stopwords=DEFAULT_STOPWORDS
)
