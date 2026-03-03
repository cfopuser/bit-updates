import io
import os
import sys
import zipfile
from unittest.mock import patch

sys.path.append(os.getcwd())

from core.downloader import download_app


class _FakeResponse:
    def __init__(self, body: bytes):
        self.status_code = 200
        self.url = "https://cdn.example.com/app.apk"
        self.headers = {
            "Content-Type": "application/vnd.android.package-archive",
            "Content-Disposition": 'attachment; filename="app.apk"',
        }
        self._body = body

    def iter_content(self, chunk_size=8192):
        for i in range(0, len(self._body), chunk_size):
            yield self._body[i:i + chunk_size]

    def close(self):
        return None


class _FakeSource:
    headers = {"User-Agent": "test"}

    def __init__(self, body: bytes):
        self.scraper = self
        self._body = body

    def get_latest_version(self, _lookup):
        return "4.100.1.0", "https://meta.example.com/release", "Waze"

    def get_download_url(self, _release_url):
        return "https://cdn.example.com/app.apk"

    def get(self, _url, stream=False, headers=None, allow_redirects=True):
        return _FakeResponse(self._body)


def _build_minimal_apk_bytes() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("AndroidManifest.xml", "<manifest package='com.waze'/>")
        zf.writestr("classes.dex", "dex")
    return buf.getvalue()


def test_aptoide_download_with_mocked_source(tmp_path):
    app_config = {
        "id": "waze_test",
        "name": "Waze Test",
        "package_name": "com.waze",
        "source": "aptoide",
        "version_file": str(tmp_path / "version.txt"),
    }
    output_apk = tmp_path / "waze_test.apk"
    fake_source = _FakeSource(_build_minimal_apk_bytes())

    with patch("core.downloader.create_source", return_value=("aptoide", fake_source, "com.waze")):
        update_needed, new_version = download_app(app_config, output_filename=str(output_apk))

    assert update_needed is True
    assert new_version == "4.100.1.0"
    assert output_apk.exists()
