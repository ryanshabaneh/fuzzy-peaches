from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.db_models import Base
import json

DATABASE_URL = "sqlite:///./entity_resolver.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def save_resolution_run(db, result: 'ResolutionResult') -> str:
    """Persist a ResolutionResult. Returns run_id."""
    from app.models.db_models import ResolutionRunDB, RecordDB, EntityDB

    run = ResolutionRunDB(
        id=result.run_id,
        created_at=result.created_at,
        config_json=result.config_used.model_dump_json(),
        stats_json=result.stats.model_dump_json(),
        warnings_json=json.dumps(result.warnings),
        errors_json=json.dumps(result.errors)
    )
    db.add(run)

    # Add entities
    for entity in result.entities:
        entity_db = EntityDB(
            id=entity.id,
            run_id=result.run_id,
            canonical_name=entity.canonical_name,
            canonical_metadata_json=json.dumps(entity.canonical_metadata),
            confidence=entity.confidence,
            matched_record_ids_json=json.dumps(entity.matched_record_ids),
            match_explanations_json=json.dumps(entity.match_explanations),
            selection_rationale_json=json.dumps(entity.selection_rationale),
            is_flagged=entity.id in result.flagged_entity_ids
        )
        db.add(entity_db)

    db.commit()
    return result.run_id
