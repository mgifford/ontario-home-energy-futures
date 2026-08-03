#!/usr/bin/env python3
"""Build the Ontario Home Energy Futures static site offline from committed
fixtures. Writes output to dist/.

    python build.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(REPO_ROOT / "src"))

from ontario_home_energy_futures.normalize.pipeline import build_observations_csv  # noqa: E402
from ontario_home_energy_futures.site.build_site import build_site  # noqa: E402
from ontario_home_energy_futures.validate.provenance import ProvenanceError  # noqa: E402


def main() -> int:
    try:
        csv_path = build_observations_csv(REPO_ROOT)
        print(f"Normalized observations written to {csv_path.relative_to(REPO_ROOT)}")
    except ProvenanceError as exc:
        print(f"ERROR: data validation failed, refusing to publish a malformed update: {exc}", file=sys.stderr)
        return 1

    output_dir = REPO_ROOT / "dist"
    build_site(REPO_ROOT, output_dir)
    print(f"Static site built to {output_dir.relative_to(REPO_ROOT)}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
