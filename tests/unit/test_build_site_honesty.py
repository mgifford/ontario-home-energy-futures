"""Guards against a specific documentation-accuracy bug found during the
hardening/red-team review (docs/RED-TEAM-REVIEW.md section 8.4): the
"What drives this result" sensitivity table on compare-timing.html was
static content that read as if computed from the user's current inputs.

See docs/CORRECTIONS.md for the corresponding errata log entry.
"""

from __future__ import annotations

from pathlib import Path

from ontario_home_energy_futures.site.build_site import build_site

REPO_ROOT = Path(__file__).parent.parent.parent


def test_sensitivity_section_does_not_claim_to_be_computed_from_current_inputs(tmp_path):
    output_dir = tmp_path / "dist"
    build_site(REPO_ROOT, output_dir)

    rendered = (output_dir / "compare-timing.html").read_text(encoding="utf-8")

    assert "for the current inputs" not in rendered, (
        "compare-timing.html must not claim the sensitivity table is "
        "computed from the user's current inputs while the underlying "
        "data is static - see docs/RED-TEAM-REVIEW.md section 8.4"
    )
    assert "Illustrative example" in rendered, (
        "the static sensitivity table must be clearly labelled as an "
        "illustrative example, not presented as computed output"
    )
    assert "not computed from your" in rendered.lower() or "not computed from the user" in rendered.lower(), (
        "an explicit 'not computed' disclosure must be present near the "
        "sensitivity table"
    )


def test_sensitivity_rows_flag_is_passed_to_template(tmp_path):
    # Regression guard: build_site.py must keep passing
    # sensitivity_rows_are_illustrative=True so the template's warning
    # callout renders; if this context key is ever removed without also
    # removing the {% if %} guard in the template, the warning would
    # silently stop appearing.
    output_dir = tmp_path / "dist"
    build_site(REPO_ROOT, output_dir)
    rendered = (output_dir / "compare-timing.html").read_text(encoding="utf-8")
    assert "callout--warning" in rendered
