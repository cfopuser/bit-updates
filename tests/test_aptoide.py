import os
import sys
from unittest.mock import Mock, patch

sys.path.append(os.getcwd())

from core.sources.aptoide import AptoideSource


def test_aptoide_metadata_parsing():
    payload = {
        "info": {"status": "OK"},
        "data": {
            "name": "Waze",
            "file": {
                "vername": "4.100.1.0",
                "path": "https://cdn.example.com/waze.apk",
                "path_alt": "https://cdn-alt.example.com/waze.apk",
            },
        },
    }

    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload

    with patch("core.sources.aptoide.requests.get", return_value=response):
        version, download_url, title = AptoideSource().get_latest_version("com.waze")

    assert version == "4.100.1.0"
    assert download_url == "https://cdn.example.com/waze.apk"
    assert title == "Waze"
