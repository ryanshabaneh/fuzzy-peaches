import pytest
from fastapi.testclient import TestClient
from main import app
from app.config.schemas import ResolverConfig
from app.config.default import DEFAULT_CONFIG

@pytest.fixture
def client():
    """FastAPI test client."""
    with TestClient(app) as c:
        yield c

@pytest.fixture
def default_config():
    """Default resolver configuration."""
    return DEFAULT_CONFIG

@pytest.fixture
def sample_csv_content():
    """Sample CSV file content."""
    return b"""id,title,artist
1,One Dance,Drake
2,One Dance - Drake,Drake
3,ONE DANCE (Radio Edit),Drake
4,Hotline Bling,Drake
5,Hotline Bling (Remix),Drake
6,Shake It Off,Taylor Swift
7,Shake it Off - Taylor Swift,Taylor Swift
"""

@pytest.fixture
def sample_json_content():
    """Sample JSON file content."""
    return b"""[
        {"id": "1", "title": "One Dance", "artist": "Drake"},
        {"id": "2", "title": "One Dance - Drake", "artist": "Drake"},
        {"id": "3", "title": "ONE DANCE (Radio Edit)", "artist": "Drake"},
        {"id": "4", "title": "Hotline Bling", "artist": "Drake"},
        {"id": "5", "title": "Shake It Off", "artist": "Taylor Swift"}
    ]"""
