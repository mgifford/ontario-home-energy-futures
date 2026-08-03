"""Static site generation: Jinja2 rendering of the 12 project pages using
computed results from ``model/``. No calculation logic lives here.
"""

from .build_site import build_site

__all__ = ["build_site"]
