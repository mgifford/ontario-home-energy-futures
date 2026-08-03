from pathlib import Path

import pytest
import yaml

from ontario_home_energy_futures.model.bill import rate_structure_from_dict

REPO_ROOT = Path(__file__).parent.parent.parent


@pytest.fixture
def hydro_ottawa_rates():
    data = yaml.safe_load(
        (REPO_ROOT / "assumptions" / "utilities" / "hydro-ottawa.yaml").read_text(encoding="utf-8")
    )
    return rate_structure_from_dict(data)


@pytest.fixture
def household_loads_assumptions():
    return yaml.safe_load(
        (REPO_ROOT / "assumptions" / "household-loads.yaml").read_text(encoding="utf-8")
    )


@pytest.fixture
def solar_assumptions():
    return yaml.safe_load((REPO_ROOT / "assumptions" / "solar.yaml").read_text(encoding="utf-8"))


@pytest.fixture
def ontario_assumptions():
    return yaml.safe_load((REPO_ROOT / "assumptions" / "ontario.yaml").read_text(encoding="utf-8"))
