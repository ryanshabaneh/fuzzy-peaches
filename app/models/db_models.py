from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import json

Base = declarative_base()

class ResolutionRunDB(Base):
    __tablename__ = "resolution_runs"

    id = Column(String, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    schema_version = Column(String, default="1.0")  # For backward compatibility
    config_json = Column(Text)  # Stored as TEXT, parsed as JSON
    stats_json = Column(Text)
    warnings_json = Column(Text)
    errors_json = Column(Text)
    result_json = Column(Text)  # Full ResolutionResult as JSON

    records = relationship("RecordDB", back_populates="run")
    entities = relationship("EntityDB", back_populates="run")

class RecordDB(Base):
    __tablename__ = "records"

    id = Column(String, primary_key=True)
    run_id = Column(String, ForeignKey("resolution_runs.id"))
    text = Column(String)
    record_metadata_json = Column(Text)  # Avoid 'metadata' - reserved by SQLAlchemy
    source_row = Column(Integer)
    normalized_text = Column(String)
    normalized_tokens_json = Column(Text)

    run = relationship("ResolutionRunDB", back_populates="records")

class EntityDB(Base):
    __tablename__ = "entities"

    id = Column(String, primary_key=True)
    run_id = Column(String, ForeignKey("resolution_runs.id"))
    canonical_name = Column(String)
    canonical_metadata_json = Column(Text)  # Avoid 'metadata'
    confidence = Column(Float)
    matched_record_ids_json = Column(Text)
    match_explanations_json = Column(Text)
    selection_rationale_json = Column(Text)
    is_flagged = Column(Boolean, default=False)

    run = relationship("ResolutionRunDB", back_populates="entities")
