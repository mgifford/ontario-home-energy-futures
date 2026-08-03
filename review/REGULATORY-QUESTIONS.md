# Regulatory Review Questions (Ontario Energy Board perspective)

See [docs/RED-TEAM-REVIEW.md §2](../docs/RED-TEAM-REVIEW.md) for this
project's own self-assessment. Check whether you agree.

## Rate and rule accuracy

- [ ] Are the modelled Hydro Ottawa time-of-use and tiered rates current?
      Check `assumptions/utilities/hydro-ottawa.yaml`'s `status` field and
      `retrieved_at` date against the live OEB `BillData.xml`
      (<https://www.oeb.ca/_html/calculator/data/BillData.xml>). As of
      this version, the project's own files admit this has **not** been
      verified against a live fetch.
- [ ] Is the 12-month net-metering credit expiry rule correctly applied
      in every code path, including across a calendar-year boundary?
      Check `tests/unit/test_net_metering.py::test_cross_year_expiry_boundary`
      and try constructing your own edge case.
- [ ] Are fixed delivery and regulatory charges preserved even at zero net
      consumption? Check
      `tests/integration/test_reference_scenario_a_standard_household.py::test_fixed_charges_remain_when_consumption_reduced`.

## Programme availability labelling

- [ ] Are currently unavailable programmes (VPP, dynamic export, capacity
      market) clearly and consistently labelled as such everywhere they
      appear? Check every file under `assumptions/value_streams/` for its
      `status.type` field and cross-check against
      `ValueStreamStatus` in `src/ontario_home_energy_futures/model/value_streams.py`.
- [ ] Does any *default* result include a value stream whose status is
      not `current`? Check `tests/unit/test_value_streams.py::test_current_ontario_bundle_only_includes_current_streams`
      and try to find a code path that bypasses this filter.

## Double-counting

- [ ] Can the same exported solar kWh receive both a net-metering credit
      and a separate export payment? Check
      `assumptions/value_stream_compatibility.yaml` and
      `tests/unit/test_compatibility.py`.
- [ ] Does an unrecorded or ambiguous compatibility relationship default
      to excluded, or to allowed? (It should default to excluded — check
      `model/compatibility.py`'s handling of unknown pairs.)

## Endorsement and status-label accuracy

- [ ] Does anything imply the OEB guarantees a specific household's
      private contract savings? (This project's self-review found no such
      claim — verify.)
- [ ] **Specific finding to check:** `assumptions/ontario.yaml` labels the
      IESO demand-growth figures `status: observed` while its own `notes`
      field says they are "pending verification." Do you agree this is a
      mislabelling? See
      [data/governance/claims.yaml](../data/governance/claims.yaml)
      `claim-ieso-demand-growth-2050` (recorded there as `needs_review`,
      not `approved`, specifically because of this inconsistency) and
      [docs/RED-TEAM-REVIEW.md §2.1](../docs/RED-TEAM-REVIEW.md).

## Reference

The Ontario Energy Board's net-metering consumer disclosure statement is
a required reference for this review:
<https://www.oeb.ca/sites/default/files/net-metering-disclosure-statement-en-20230501.pdf>.
Compare its consumer-protection expectations against what this
application currently discloses (see
[MODEL_CARD.md](../MODEL_CARD.md) "Financial risks").
