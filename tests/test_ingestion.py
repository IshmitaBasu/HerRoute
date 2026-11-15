import csv
import json
import zipfile
from io import BytesIO

import pytest

from src.ingestion import download


class Response:
    url = "https://example.test/data"
    headers = {}

    def __init__(self, data=None, content=b""):
        self.data, self.content = data, content

    def raise_for_status(self):
        pass

    def json(self):
        return self.data

    def iter_content(self, size):
        yield self.content


def test_lights_accepts_multipoints_and_rejects_invalid_coordinates(monkeypatch, tmp_path):
    data = {"type": "FeatureCollection", "features": [{"geometry": {"type": "MultiPoint", "coordinates": [[13.4, 52.52]]}}]}
    monkeypatch.setattr(download.requests, "get", lambda *a, **k: Response(data))
    assert download.download_lights(tmp_path)["count"] == 1
    data["features"][0]["geometry"]["coordinates"] = [[0, 0]]
    with pytest.raises(ValueError):
        download.download_lights(tmp_path)


def test_stops_are_filtered_to_bounds(monkeypatch, tmp_path):
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr("stops.txt", "stop_id,stop_name,stop_lat,stop_lon\n1,inside,52.52,13.4\n2,outside,0,0\n")
    monkeypatch.setattr(download.requests, "get", lambda *a, **k: Response(content=buf.getvalue()))
    assert download.download_stops(tmp_path)["count"] == 1
    with (tmp_path / "stops.csv").open(encoding="utf-8") as f:
        assert [row["stop_id"] for row in csv.DictReader(f)] == ["1"]


def test_truncated_lighting_response_is_rejected(monkeypatch, tmp_path):
    data = {"type": "FeatureCollection", "numberMatched": 2, "features": [
        {"geometry": {"type": "Point", "coordinates": [13.4, 52.52]}}]}
    monkeypatch.setattr(download.requests, "get", lambda *a, **k: Response(data))
    with pytest.raises(ValueError, match="truncated"):
        download.download_lights(tmp_path)


def test_failed_run_does_not_leave_old_manifest(monkeypatch, tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps({"old": True}))
    monkeypatch.setattr(download, "OUT", tmp_path)
    def fail(_):
        raise ValueError("failure")
    monkeypatch.setattr(download, "download_lights", fail)
    with pytest.raises(ValueError):
        download.main()
    assert not (tmp_path / "manifest.json").exists()
