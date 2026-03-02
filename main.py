from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.api.routes import router
from app.models.database import init_db
from app.config.default import DEFAULT_CONFIG

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("Database initialized")
    logger.info(f"Default config: {DEFAULT_CONFIG.model_dump_json(indent=2)}")
    yield


app = FastAPI(
    title="Fuzzy Entity Resolver",
    description="Resolve duplicate entities in messy datasets",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration for local dev + deployed frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://fuzzy-peaches.vercel.app",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def root():
    return {"status": "ok", "docs": "/docs", "health": "/health"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
