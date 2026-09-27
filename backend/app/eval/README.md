# Evaluation harness (stub)

Deliberately not built out in this pass -- this is a prototype, and the
design doc's full evaluation plan (300-parcel hand-labeled set, per-hazard
ground-truth comparisons against OpenFEMA/GNSS/state fire perimeters/NOAA
heat data/NAIP imagery, rank correlation, precision/recall) is real work
for a later phase, not scaffold work.

What exists here: `rule_vs_jev_harness.py` defines the function signature
Phase 3's gate needs ("Jev beats baseline") so that when labeled data
exists, wiring it in is mechanical rather than a redesign.

## What Phase 3's gate actually requires (for later)

- A `LabeledParcel` set (~300 parcels, hand-assigned hazard levels from
  evidence, ideally reviewed by someone with planning/insurance experience).
- Run both `app.scoring.rule_baseline` and `app.scoring.jev_client` against
  each labeled parcel's feature state.
- Compare accuracy and calibration (when Jev says 80% confident, is it
  right ~80% of the time?).
- Tune `JEV_CONFIDENCE_THRESHOLD` on a held-out split; report how many
  reports it routes to `needs_expert_review`.
- Jev must beat the rule baseline before it ships as the default scorer.
