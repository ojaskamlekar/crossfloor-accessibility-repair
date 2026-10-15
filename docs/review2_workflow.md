# Second review: auditable workflow and completion gates

The 17 requested items are preserved in `review2_requirements.md`. Work continues
from the merged first revision, not from a replacement research direction.
Publication authorization follows the user's ongoing fork/PR instruction.

## Reproduction

Use Python >=3.11 and install `requirements-review.lock.txt` and the local
package. Keep the pinned IFC sources and original audit outputs outside Git.
Recreate those audits with `download_public_buildings.py` and
`public_building_controlled.py` under their recorded source/license hashes.
Never infer original doors merely because two room boundaries touch.

Small smoke test (may run from a dirty tree; excluded from paper evidence):

```bash
python -m pytest tests/test_review_revision.py tests/test_review2_protocol.py
python scripts/review2_benchmarks.py --config docs/review2_smoke.json --output runs/review2-smoke-NEW --smoke
```

After committing code, the complete sequential campaign is:

```bash
python scripts/review2_campaign.py --audits data/derived/review-public-consecutive/audits --output runs/review2-final
```

It validates and exports multi-room subsets, executes routine, boundary,
ablation and public suites, replays each returned action set, audits raw records
and renders figures. Every output directory must be fresh; failed runs are
retained, never silently overwritten. The paper summary rejects missing repeats,
dirty evidence, mismatched sources/inputs, exact-solver disagreements and
internal errors. Repetition-level caps/timeouts are legitimate retained outcomes.

The existing IEEE build remains available for historical evidence. Add
`--review2 runs/review2-final/summary` to `build_ieee_master.py`, with its existing
required historical evidence/figure arguments, to insert the new measured
section. `make_ieee_figures.py` now additionally renders the complete authored
diagnostic. Compile normally using the unchanged IEEE class; verify all pages.
No venue page cap or authorship is inferred.

## Protocol fixed before collection

- `review2_protocol.json`: five fresh processes per routine solver/input; seeds
  0,1,2; seven declared structural families and two routine sizes each.
- `review2_boundary.json`: three processes per expensive case; same three seeds;
  declared larger connectivity/profile/owner/cyclic sizes, including operational
  boundaries. Same 10,000 raw-state and 65,536 cut-column caps for DP modes.
- `review2_ablation.json`: five processes; pruning, compression, reversed valid
  processing order and pure geometry memoization controls. Identical-state
  least-label dominance is not disabled, and no such result is claimed.
- `review2_public.json`: three fresh processes per expensive public variant;
  one selected Molio subset, not an independent building per variant.
- Small-instance oracle runs once for correctness, not as a repeated timing
  competitor. Every completed exact status/cost/count/ID tuple must agree.

Geometry is fixed within each family size. Seeds perturb prices and solver seed;
they are not independent geometric building samples. Connectivity-family growth
also increases collision-cell count; cyclic growth also increases support span.
The family descriptions state those couplings instead of claiming a fully
isolated factorial design. All declared sizes, favorable/unfavorable compression
cases, timeouts and caps are reported.

All methods import before a READY handshake, then receive the same hard wall
budget per suite. Primary function wall time includes validation, recognition,
optimization and its internal replay; a separate independent selected-set replay
is outside that measured function but inside the hard worker budget. Startup
and imports are excluded from function time and included in process peak RSS.
Hardware, package versions, affinity, inherited cgroup limit and address-space
rlimit are recorded. No extra address-space cap or isolated CPU is asserted.
Timeout memory/time values are null when unavailable; the configured timeout
is displayed separately, not substituted as an observed completion time.

Pure geometry memoization stores only immutable polygon coordinates and room
free-centre-space (8,192/2,048-entry LRU bounds). All solver methods start with
empty caches. It never caches a selection's validity, route or recognized
instance. The uncached ablation disables both caches. Activation compilation
still validates every selected action combination; full recognition caching and
spatial-index acceleration remain unimplemented. The footprint-intersection
counter covers actual non-same-owner portal intersections in additional geometry
compilation calls; it does not pretend to count all predicates in schema or
baseline validation. Cell coverage tests are counted separately.

The relative cost gap is `max(0,U-L)/max(1,abs(U))`, using the reported lower
bound and incumbent original cost. If the cost stage is OPTIMAL, the cost bound
and gap are exact even if a later count/ID stage is interrupted. Other CP-SAT
bounds are explicitly floating estimates and withheld if scaled integer totals
exceed 2^53. Unknown measurements remain null. Cost-optimal is not automatically
an optimal full lexicographic label.

## Required result fields

`results.json` stores experiment/input/source/subset/variant IDs, input hash,
commit, family/size/seed, solver settings, repeat, status, objective cost/count,
selected original IDs, cost bound/precision/gap, end-to-end time, phase times,
process peak RSS, generated/deduplicated/retained/peak states, cut/group sizes,
reduction time, replay record path, route and topology results. Each instance
also has a description containing source storeys, room counts, adjacency/access
counts, required destinations, candidates/assets/cells and measured interface
parameters. Missing values are null, never manufactured zero measurements.

## Seventeen-item gate tracker

| Item | Concrete deliverable | Remaining scientific boundary |
|---|---|---|
| 1. Novelty | `review2_positioning.md`, algorithmic model table in manuscript | Supported transfer/bound is precise; broad priority against tighter domain-valued resource DPs remains open. |
| 2. Complete example | `diagnostic_example`, hand-derived optimum and false purchase-vertex check; four-panel figure | Authored mechanism demonstration, not BIM provenance. |
| 3. Theory | `review2_theory_package.md`, notation table and named-procedure proof appendix | Independent proof review remains necessary; a proof package is not an endorsement. |
| 4. Hardness | Explicit threshold/cost-preserving physical Set Cover construction, constants/growing parameters | Classical inherited hardness, no new ETH/exponent result. |
| 5. Multi-room | Largest admitted consecutive Molio block: four storeys, eight unchanged rooms, nonempty adjacency; paired permission control | All access annotations are hypothetical; four screened sources excluded. No validated original-door repair. |
| 6. Denominators | Explicit source/subset/variant/run identifiers and source-overlap statement | Historical Molio and Duplex variants never count as new independent source buildings. |
| 7. Scaling | Seven declared generator families plus larger boundary protocol | Some parameters are coupled and stated; not all realistic geometries are covered. |
| 8. Compression | Complete cyclic/unfavorable grids; rows/time/RSS/caps retained | Practical role depends on executed results, not a selected favorable instance. |
| 9. CP-SAT | Cost-stage bounds, incumbents, fair post-READY budgets, every solution replayed | Checked int64 range; shared geometry; empirical superiority may favor CP-SAT. |
| 10. Greedy | Full-action deletion plus bounded 0--2-out/0--2-in exchanges; known dead-end rescue | Deterministic bounded heuristic, not complete or an approximation guarantee. |
| 11. Recognition | Phase timers, scoped counters, pure immutable memoization and uncached control | No full recognition-cache or spatial-index implementation claimed. |
| 12. Reliability | Pinned clean commits, fixed seeds, five/three fresh-process policy, IQR and all failures | Descriptive workstation evidence; no isolated-hardware significance claim. |
| 13. Ablations | Pruning, representative reduction, valid reversed orders, memoization | No dominance-off claim; altered semantics remain a distinct control category. |
| 14. Shared errors | Hand optima, metamorphic tests, independent rectangle/route checker | Does not independently implement all containment/obstacle/clearance geometry. |
| 15. Artifact | One campaign, standardized schema, audit, solution replay, figure generator and smoke path | Public licenses and source download availability still apply. |
| 16. Writing | Operational definitions, supplied candidates/exactness, full example, focused limitation, scoped contributions | Extended master still needs an actual venue/authorship/page policy. |
| 17. Final gates | This explicit tracker plus measured execution report | Do not label submission-ready while novelty/proof-review/authenticated-building gates remain open. |
