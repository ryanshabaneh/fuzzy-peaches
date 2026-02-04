import pytest
import json
from io import BytesIO

class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

class TestConfigEndpoint:
    def test_get_default_config(self, client):
        response = client.get("/config/default")
        assert response.status_code == 200

        config = response.json()
        assert "weights" in config
        assert "thresholds" in config
        assert config["weights"]["token_jaccard"] == 0.4

class TestResolveEndpoint:
    def test_resolve_csv(self, client, sample_csv_content):
        response = client.post(
            "/resolve",
            files={"file": ("test.csv", sample_csv_content, "text/csv")},
            data={"column_mapping_json": json.dumps({"id": "id", "text": "title", "artist": "artist"})}
        )

        assert response.status_code == 200
        result = response.json()

        assert "entities" in result
        assert "stats" in result
        assert result["stats"]["total_records"] == 7

    def test_resolve_json(self, client, sample_json_content):
        response = client.post(
            "/resolve",
            files={"file": ("test.json", sample_json_content, "application/json")},
            data={"column_mapping_json": json.dumps({"id": "id", "text": "title", "artist": "artist"})}
        )

        assert response.status_code == 200
        result = response.json()
        assert len(result["entities"]) > 0

    def test_invalid_config_returns_400(self, client, sample_csv_content):
        response = client.post(
            "/resolve",
            files={"file": ("test.csv", sample_csv_content, "text/csv")},
            data={
                "column_mapping_json": json.dumps({"id": "id", "text": "title", "artist": "artist"}),
                "config_json": json.dumps({
                    "weights": {"token_jaccard": 0.9, "edit_distance": 0.9}  # Sums > 1
                })
            }
        )

        assert response.status_code == 400
        assert "sum to 1.0" in response.json()["detail"].lower()

    def test_empty_file_returns_400(self, client):
        response = client.post(
            "/resolve",
            files={"file": ("test.csv", b"", "text/csv")}
        )

        assert response.status_code == 400
