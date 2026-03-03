import os
import sys
from unittest.mock import Mock

sys.path.append(os.getcwd())

from core.sources.apkmirror import APKMirrorSource


def test_apkmirror_latest_version_parsing():
    source = APKMirrorSource(timeout=0)
    response = Mock()
    response.status_code = 200
    response.text = """
    <html>
      <body>
        <div class="appRow">
          <h5 class="appRowTitle">Bit 7.19.1</h5>
          <a class="downloadLink" href="/apk/example/bit-7-19-1-release/"></a>
        </div>
      </body>
    </html>
    """
    source.scraper = Mock()
    source.scraper.get.return_value = response

    version, release_url, title = source.get_latest_version("com.bnhp.payments.paymentsapp")

    assert version == "7.19.1"
    assert title == "Bit 7.19.1"
    assert release_url.endswith("/apk/example/bit-7-19-1-release/")
