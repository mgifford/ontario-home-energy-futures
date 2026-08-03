"""Live retrieval of the OEB BillData.xml (Phase 2).

Not invoked by the offline build (``build.py``); used only by the scheduled
``update-data.yml`` GitHub Actions workflow. Kept separate from ``normalize``
so that parsing/validation logic can be tested without any network access.
"""

from __future__ import annotations

import urllib.request
from pathlib import Path

OEB_BILLDATA_URL = "https://www.oeb.ca/_html/calculator/data/BillData.xml"


def fetch_oeb_billdata(destination: Path, *, url: str = OEB_BILLDATA_URL, timeout: int = 30) -> Path:
    """Download the live OEB BillData.xml to ``destination``.

    Callers are responsible for hashing the result and recording it as a new
    entry in ``data/source-manifest.yaml`` rather than overwriting an
    existing raw file in place.
    """
    request = urllib.request.Request(url, headers={"User-Agent": "ontario-home-energy-futures"})
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        data = response.read()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    return destination
