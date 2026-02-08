import pytest
import json

from app.api import routes as api_routes


@pytest.fixture(autouse=True)
def reset_rate_limit_state():
    api_routes.REQUEST_TIMESTAMPS_BY_IP.clear()
    yield
    api_routes.REQUEST_TIMESTAMPS_BY_IP.clear()

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

    def test_too_large_payload_returns_413_or_400(self, client):
        oversized_content = b"x" * (5 * 1024 * 1024 + 1)

        response = client.post(
            "/resolve",
            files={"file": ("oversized.csv", oversized_content, "text/csv")}
        )

        assert response.status_code in (413, 400)
        assert "large" in response.json()["detail"].lower()

    def test_too_many_records_returns_413_or_400(self, client):
        rows = ["id,title,artist"]
        rows.extend(f"{i},Song {i},Artist {i}" for i in range(1, 20_002))
        csv_content = ("\n".join(rows)).encode("utf-8")

        response = client.post(
            "/resolve",
            files={"file": ("too_many_rows.csv", csv_content, "text/csv")},
            data={"column_mapping_json": json.dumps({"id": "id", "text": "title", "artist": "artist"})}
        )

        assert response.status_code in (413, 400)
        assert "too many records" in response.json()["detail"].lower()

    def test_rate_limit_returns_429_after_10_requests(self, client):
        csv_content = b"id,title,artist\n1,Song One,Artist One\n"
        data = {"column_mapping_json": json.dumps({"id": "id", "text": "title", "artist": "artist"})}

        for _ in range(10):
            response = client.post(
                "/resolve",
                files={"file": ("small.csv", csv_content, "text/csv")},
                data=data
            )
            assert response.status_code == 200

        response = client.post(
            "/resolve",
            files={"file": ("small.csv", csv_content, "text/csv")},
            data=data
        )

        assert response.status_code == 429
        assert response.json()["detail"] == "Rate limit exceeded, try again later."

    def test_rate_limit_uses_x_forwarded_for(self, client):
        csv_content = b"id,title,artist\n1,Song One,Artist One\n"
        data = {"column_mapping_json": json.dumps({"id": "id", "text": "title", "artist": "artist"})}
        headers = {"x-forwarded-for": "1.2.3.4"}

        for _ in range(10):
            response = client.post(
                "/resolve",
                files={"file": ("small.csv", csv_content, "text/csv")},
                data=data,
                headers=headers,
            )
            assert response.status_code == 200

        response = client.post(
            "/resolve",
            files={"file": ("small.csv", csv_content, "text/csv")},
            data=data,
            headers=headers,
        )

        assert response.status_code == 429
        assert "1.2.3.4" in api_routes.REQUEST_TIMESTAMPS_BY_IP
