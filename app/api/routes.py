from fastapi import APIRouter, UploadFile, HTTPException, Depends, Form
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.orm import Session
import json

from app.models.schemas import ResolutionResult
from app.config.schemas import ResolverConfig
from app.config.default import DEFAULT_CONFIG
from app.loaders.factory import get_loader
from app.core.pipeline import EntityPipeline
from app.models.database import get_db, save_resolution_run
from app.models.db_models import ResolutionRunDB

router = APIRouter()

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


class RunSummary(BaseModel):
    run_id: str
    created_at: datetime
    total_records: int
    total_entities: int


@router.get("/health")
async def health():
    return {"status": "healthy", "version": "1.0.0"}


@router.get("/config/default", response_model=ResolverConfig)
async def get_default_config():
    """Return default configuration for UI preview."""
    return DEFAULT_CONFIG


@router.post("/resolve", response_model=ResolutionResult)
async def resolve_entities(
    file: UploadFile,
    config_json: Optional[str] = Form(None),
    column_mapping_json: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """
    Upload CSV/JSON file and run entity resolution.

    - file: CSV or JSON file to process
    - config_json: Optional ResolverConfig as JSON string
    - column_mapping_json: Optional column mapping as JSON string
    """
    # Read file content
    contents = await file.read()

    await file.seek(0)

    # Validate file size
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // 1024 // 1024}MB"
        )

    # Parse config
    if config_json:
        try:
            config_dict = json.loads(config_json)
            config = ResolverConfig.model_validate(config_dict)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid config JSON: {e}")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid config: {e}")
    else:
        config = DEFAULT_CONFIG

    # Parse column mapping
    if column_mapping_json:
        try:
            column_mapping = json.loads(column_mapping_json)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid column mapping JSON: {e}")
    else:
        column_mapping = {}

    # Get appropriate loader
    try:
        loader, detected_format = get_loader(file.filename, contents)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Validate file
    is_valid, validation_errors = loader.validate(contents)
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail=f"File validation failed: {'; '.join(validation_errors)}"
        )

    # Load records
    records, load_warnings = loader.load(contents, column_mapping)

    if not records:
        raise HTTPException(
            status_code=400,
            detail="No valid records found in file"
        )

    # Run pipeline
    pipeline = EntityPipeline(config)
    result = pipeline.resolve(records)

    # Add load warnings to result
    result.warnings = load_warnings + result.warnings

    # Persist result
    save_resolution_run(db, result)

    return result


@router.get("/runs", response_model=List[RunSummary])
async def list_runs(db: Session = Depends(get_db)):
    """List all resolution runs with summary stats."""
    runs = db.query(ResolutionRunDB).order_by(ResolutionRunDB.created_at.desc()).all()

    summaries = []
    for run in runs:
        stats = json.loads(run.stats_json) if run.stats_json else {}
        summaries.append(RunSummary(
            run_id=run.id,
            created_at=run.created_at,
            total_records=stats.get("total_records", 0),
            total_entities=stats.get("total_entities", 0),
        ))

    return summaries


@router.get("/runs/{run_id}", response_model=ResolutionResult)
async def get_run(run_id: str, db: Session = Depends(get_db)):
    """Get results of a previous resolution run."""
    run = db.query(ResolutionRunDB).filter(ResolutionRunDB.id == run_id).first()

    if not run or not run.result_json:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    return ResolutionResult.model_validate_json(run.result_json)
