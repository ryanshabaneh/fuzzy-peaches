from fastapi import APIRouter, UploadFile, HTTPException, Depends, Query, Form
from typing import Optional, Dict
import json

from app.models.schemas import ResolutionResult, Entity
from app.config.schemas import ResolverConfig
from app.config.default import DEFAULT_CONFIG
from app.loaders.factory import get_loader
from app.core.pipeline import EntityPipeline
from app.models.database import get_db, save_resolution_run

router = APIRouter()

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


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
):
    """
    Upload CSV/JSON file and run entity resolution.

    - file: CSV or JSON file to process
    - config_json: Optional ResolverConfig as JSON string
    - column_mapping_json: Optional column mapping as JSON string
    """
    # Read file content
    contents = await file.read()

    # IMPORTANT: Reset stream position for potential re-reads
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

    return result


@router.get("/runs/{run_id}", response_model=ResolutionResult)
async def get_run(run_id: str):
    """Get results of a previous resolution run."""
    # TODO: Implement database lookup
    raise HTTPException(status_code=404, detail=f"Run {run_id} not found")


@router.get("/entities/{run_id}/{entity_id}", response_model=Entity)
async def get_entity(run_id: str, entity_id: str):
    """Get single entity with full details."""
    # TODO: Implement database lookup
    raise HTTPException(status_code=404, detail=f"Entity {entity_id} not found")
