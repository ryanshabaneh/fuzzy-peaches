from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.api.routes import router
from app.models.database import init_db
from app.config.default import DEFAULT_CONFIG

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Fuzzy Entity Resolver",
    description="Resolve duplicate entities in messy datasets",
    version="1.0.0"
)

# CORS — permissive for deployment; lock down origins in production if needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
async def startup():
    init_db()
    logger.info("Database initialized")
    logger.info(f"Default config: {DEFAULT_CONFIG.model_dump_json(indent=2)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
