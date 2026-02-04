import pytest
from app.core.pipeline import EntityPipeline
from app.models.schemas import Record
from app.config.schemas import ResolverConfig, ThresholdConfig
from app.config.default import DEFAULT_CONFIG

class TestEntityPipeline:
    @pytest.fixture
    def pipeline(self, default_config):
        return EntityPipeline(default_config)

    @pytest.fixture
    def sample_records(self):
        return [
            Record(id="1", text="One Dance - Drake", record_metadata={"artist": "Drake"}, source_row=1),
            Record(id="2", text="Drake - One Dance", record_metadata={"artist": "Drake"}, source_row=2),
            Record(id="3", text="ONE DANCE", record_metadata={"artist": "Drake"}, source_row=3),
            Record(id="4", text="Hotline Bling", record_metadata={"artist": "Drake"}, source_row=4),
            Record(id="5", text="Shake It Off", record_metadata={"artist": "Taylor Swift"}, source_row=5),
        ]

    def test_groups_duplicates(self, pipeline, sample_records):
        result = pipeline.resolve(sample_records)

        # Should have at least 3 entities: One Dance, Hotline Bling, Shake It Off
        assert len(result.entities) >= 3

        # Find One Dance entity
        one_dance = next(
            (e for e in result.entities if "dance" in e.canonical_name.lower()),
            None
        )
        assert one_dance is not None
        assert len(one_dance.matched_record_ids) == 3

    def test_keeps_distinct_separate(self, pipeline, sample_records):
        result = pipeline.resolve(sample_records)

        # Hotline Bling and Shake It Off should be separate
        hotline = next(
            (e for e in result.entities if "hotline" in e.canonical_name.lower()),
            None
        )
        shake = next(
            (e for e in result.entities if "shake" in e.canonical_name.lower()),
            None
        )

        assert hotline is not None
        assert shake is not None
        assert hotline.id != shake.id

    def test_higher_threshold_fewer_matches(self, sample_records):
        # Low threshold config
        low_config = DEFAULT_CONFIG.model_copy(
            update={
                "thresholds": ThresholdConfig(high_confidence=0.6, low_confidence=0.5)
            }
        )
        low_result = EntityPipeline(low_config).resolve(sample_records)

        # High threshold config
        high_config = DEFAULT_CONFIG.model_copy(
            update={
                "thresholds": ThresholdConfig(high_confidence=0.95, low_confidence=0.9)
            }
        )
        high_result = EntityPipeline(high_config).resolve(sample_records)

        # Higher threshold should produce more entities (fewer merges)
        assert len(high_result.entities) >= len(low_result.entities)

    def test_empty_input(self, pipeline):
        result = pipeline.resolve([])

        assert result.entities == []
        assert result.stats.total_records == 0
        assert len(result.errors) == 0

    def test_single_record(self, pipeline):
        records = [Record(id="1", text="Only One", record_metadata={}, source_row=1)]
        result = pipeline.resolve(records)

        assert len(result.entities) == 1
        assert result.entities[0].confidence == 1.0

    def test_config_preserved_in_result(self, pipeline, sample_records):
        result = pipeline.resolve(sample_records)

        # Config should be frozen copy in result
        assert result.config_used is not None
        assert result.config_used.weights.token_jaccard == 0.4
