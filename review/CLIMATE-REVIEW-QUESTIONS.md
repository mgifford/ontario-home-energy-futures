# Climate and Lifecycle Review Questions

See [docs/RED-TEAM-REVIEW.md §5](../docs/RED-TEAM-REVIEW.md) and
[docs/ENVIRONMENTAL-CLAIMS-POLICY.md](../docs/ENVIRONMENTAL-CLAIMS-POLICY.md).

## Current state — verify the absence

- [ ] Search `web/templates/` for "emissions," "carbon," "CO2," "green,"
      or "clean." As of this version, none should be found. Confirm.
- [ ] Search for any implicit environmental framing (e.g., colour choices,
      icons, or phrasing that implies environmental virtue without an
      explicit substantiated claim). This project's self-review checked
      only for textual claims — a visual-framing check is a genuine gap
      you may be positioned to fill.

## If/when an emissions module is added (future work — review readiness now)

- [ ] Does `docs/ENVIRONMENTAL-CLAIMS-POLICY.md` correctly anticipate the
      distinctions a real Ontario grid-emissions model would need
      (marginal vs. average, operational vs. embodied, timing of
      consumption, location of grid constraints)? Are there distinctions
      it's missing?
- [ ] Does the policy's list of prohibited terms match current Competition
      Bureau of Canada greenwashing guidance?
      (<https://competition-bureau.canada.ca/en/deceptive-marketing-practices/greenwashing-guidance-businesses>)
- [ ] Is the "zero operational emissions at the point of generation"
      exception worded narrowly enough to avoid being read as a broader
      claim?

## Climate as a planning condition, not a sales argument

- [ ] Does anything in this project imply a specific future outage date,
      frequency, or storm-loss amount? (None should exist yet — this
      project has not yet built its climate/extreme-weather module; see
      [docs/RED-TEAM-REVIEW.md](../docs/RED-TEAM-REVIEW.md) "Deferred to
      next phase.")
- [ ] When that module is built, will it correctly explain return periods
      (e.g., a "1-in-20-year" event means an estimated 5% chance per year,
      not a fixed schedule, and consecutive-year occurrence is possible)?
      Check against ClimateData.ca guidance (<https://climatedata.ca/>)
      when reviewing that future work.

## Dispatch policy trade-offs (future work)

- [ ] When battery/EV dispatch optimization is built, can the tool show a
      financially optimized dispatch and a carbon-optimized dispatch
      disagreeing? `docs/ENVIRONMENTAL-CLAIMS-POLICY.md` commits to this;
      hold the implementation to that commitment when it lands.

## Report what you find

If you find an environmental claim this review missed, or a place where
absence-of-claim is not actually true, see
[docs/CORRECTIONS.md](../docs/CORRECTIONS.md) — this is a "type: unsupported
claim was published" finding, which is treated as a correction-worthy
error, not a minor issue.
