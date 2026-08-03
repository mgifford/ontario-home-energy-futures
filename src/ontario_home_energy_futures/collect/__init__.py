"""Data collection: retrieve raw source files.

Phase 1 relies on committed fixtures under ``data/raw/`` (see
``data/source-manifest.yaml``) so the project builds fully offline. The
``fetch_oeb_billdata`` function is provided for Phase 2's scheduled update
workflow and is not exercised during an offline build.
"""

from .oeb_fetch import fetch_oeb_billdata

__all__ = ["fetch_oeb_billdata"]
