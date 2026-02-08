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
    """Persist a ResolutionResult as a single JSON blob. Returns run_id."""
    from app.models.db_models import ResolutionRunDB

    run = ResolutionRunDB(
        id=result.run_id,
        created_at=result.created_at,
        result_json=result.model_dump_json(),
        stats_json=result.stats.model_dump_json(),
    )
    db.add(run)
    db.commit()
    return result.run_id
