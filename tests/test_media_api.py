import os
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db import init_db, save_media_item

TEST_MEDIA_DB = "test_media_api.db"

@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch):
    if os.path.exists(TEST_MEDIA_DB):
        try:
            os.remove(TEST_MEDIA_DB)
        except Exception:
            pass
    monkeypatch.setenv("REPOS_DB_PATH", TEST_MEDIA_DB)
    init_db(TEST_MEDIA_DB)
    yield
    if os.path.exists(TEST_MEDIA_DB):
        try:
            os.remove(TEST_MEDIA_DB)
        except Exception:
            pass

client = TestClient(app)

def test_list_media_empty():
    resp = client.get("/api/media")
    assert resp.status_code == 200
    assert resp.json() == []

def test_extract_media_mocked(monkeypatch):
    async def mock_extract(url):
        return {
            "title": "Vídeo Incrível de Jardinagem",
            "author": "Jardim Fácil",
            "description": "Dicas de poda de oliveiras no outono.",
            "duration_seconds": 120,
            "thumbnail_url": "https://example.com/thumb.jpg",
            "source": "Facebook",
            "stream_url": "https://example.com/video.mp4",
            "media_type": "video"
        }

    from backend.app import main
    monkeypatch.setattr(main, "extract_media_info", mock_extract)

    resp = client.post("/api/media/extract", json={"url": "https://www.facebook.com/watch/?v=12345"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Vídeo Incrível de Jardinagem"
    assert data["source"] == "Facebook"
    assert data["duration_seconds"] == 120

def test_process_media_mocked(monkeypatch):
    async def mock_process(url, download_video=True, db_path=None):
        return save_media_item(
            url=url,
            title="Dicas de Tratamento de Água de Piscina",
            author="Piscina Limpa",
            description="Como regular o cloro e pH rapidamente.",
            summary_ai="Guia prático para manter a água cristalina e com níveis equilibrados de pH e cloro.",
            category="Piscinas",
            thumbnail_url="https://example.com/pool.jpg",
            media_type="video",
            local_file_path="",
            duration_seconds=180,
            source="Facebook",
            db_path=db_path or TEST_MEDIA_DB
        )

    from backend.app import main
    monkeypatch.setattr(main, "process_and_save_media", mock_process)

    resp = client.post("/api/media/process", json={"url": "https://www.facebook.com/watch/?v=98765", "download_video": False})
    assert resp.status_code == 200
    item = resp.json()
    assert item["id"] > 0
    assert item["category"] == "Piscinas"
    assert "Guia prático" in item["summary_ai"]

    # Test list filter
    list_resp = client.get("/api/media?category=Piscinas")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    # Test delete
    del_resp = client.delete(f"/api/media/{item['id']}")
    assert del_resp.status_code == 200
    assert del_resp.json()["success"] is True

    # Check after delete
    check_resp = client.get("/api/media")
    assert check_resp.json() == []

def test_stream_media(tmp_path):
    dummy_video = tmp_path / "test_video.mp4"
    dummy_content = b"VIDEO_HEADER_1234567890_STREAM_DATA"
    dummy_video.write_bytes(dummy_content)

    item = save_media_item(
        url="https://facebook.com/video/1",
        title="Streaming Test",
        local_file_path=str(dummy_video),
        db_path=TEST_MEDIA_DB
    )
    media_id = item["id"]

    # 1. Full stream
    resp = client.get(f"/api/media/{media_id}/stream")
    assert resp.status_code == 200
    assert resp.content == dummy_content
    assert resp.headers["accept-ranges"] == "bytes"

    # 2. Range request (e.g. Safari / iPhone request)
    range_resp = client.get(f"/api/media/{media_id}/stream", headers={"Range": "bytes=0-11"})
    assert range_resp.status_code == 206
    assert range_resp.content == dummy_content[0:12]
    assert "bytes 0-11/" in range_resp.headers["content-range"]

def test_errors():
    resp = client.post("/api/media/extract", json={"url": ""})
    assert resp.status_code == 400

    resp = client.post("/api/media/process", json={"url": ""})
    assert resp.status_code == 400

    resp = client.delete("/api/media/999999")
    assert resp.status_code == 404
