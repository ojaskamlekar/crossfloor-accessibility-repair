# Inspectable theory package (15 October 2026)

This is a constructive transfer to the supplied finite physical-template model,
not a new representative-basis primitive or a claim of literature priority.
Implementation: `interface_recognition.py`, `dp_owned_interface.py` and
`representative_partitions.py`. Existing detailed proofs remain in
`asset_unit_interface_theorem.md`, `owner_multiplicity_refinement.md` and the
manuscript proof appendix. The named operations below are pseudocode procedures,
not promises of identically named Python functions.

## Recognized class and supplied versus constructed structure

Supplied: ordered/elevated frozen room polygons and IDs, baseline doors/portals,
profile specifications, rooted demands and a finite catalogue of independent
nonnegative-cost physical activation actions. No candidate doors, geometry edits,
dependencies or declared action exclusions are admitted. Existing doors are
allowed. Actions may have disconnected supplied effects. An owner denotes one
consistent kind/profile/width/footprint asset; reuse is permitted only for the
same verified owner. Every active portal has two aligned rectangular footprints,
valid endpoint landings, reservation containment and obstacle clearance.

Computed: per-profile within-floor baseline components, exact owner/cell
incidences in the kernel, action/owner incidence components (complete units),
unit spans, baseline spans and the floor event schedule. Geometry compilation
must agree with the constructed cell conflicts for every available action pair;
otherwise recognition rejects the input. Tiny cells at or below EPS are rejected.
The algorithm does not assume that an arbitrary BIM already supplies a bounded
decomposition. The recognizer constructs it and measures its width. The theorem
is conditional on this recognized class and uses its actual measured parameters.

## Notation and measurement

| Symbol | Meaning and measurement | Supplied or computed | Runtime role |
|---|---|---|---|
| F,m | Floors; original actions | Supplied counts | Polynomial event/input size |
| p | Number of separate profile layers, including vacuous layers | Supplied count | Connectivity product |
| r | Maximum within-floor baseline component count in one profile; marked-component version only when pruning is enabled | Computed union-find and optional marking | At most prL optional non-anchor positions |
| z | Maximum positive-area owned collision cells on one floor | Computed rectangular arrangement | At most zL live resources |
| L | Maximum consecutive-floor span of a **complete unit**, or active baseline cross-floor edge, at least one | Computed from sorted floor ranks | Look-ahead window and forgetting |
| h(J,c), h | Owners in unit J capable of using cell c; maximum across unit/cell pairs | Computed from full action footprints | h(J,c)+2 resource statuses |
| g | Maximum owners in a unit | Computed; descriptive only | Not a separate exponent in refined bound |
| B | Discrete input bit length, including costs, original IDs and represented incidences | Supplied encoding length | Exact label arithmetic/storage |
| T_rec | Validation, activation geometry, cells, pair-conflict agreement, components and units | Measured preprocessing | Additive, not omitted from end-to-end cost |
| K,C | Implementation raw-state and cut-column caps | Supplied run settings | Operational limits; absent from mathematical theorem |

The geometric kernel uses metres, binary floating-point coordinates and
EPS=1e-8 for the predicates documented in `geometry.py`; this is not an exact
rational computational-geometry guarantee. The post-recognition optimization
and decimal objective are exact for the recognized discrete contract. T_rec
is kept explicit rather than claiming GEOS has a symbolic bit-complexity bound.

## Event invariant and lemma dependencies

At a fixed event, each stored history has a complete selected prefix of original
actions, its full paid occupancy on every live floor, and one optional rooted
route witness per profile. Every demanded component already introduced is
selected. Witness blocks describe precisely the connectivity of selected live
positions and the permanent anchor after forgotten positions are eliminated.
No closed non-anchor witness component has been forgotten. The label is exact
total cost, original action count and sorted original IDs for that history.
Within a unit, occupancy preserves current owner identities; outside it, only
external occupancy remains. Reduction preserves the least accepting label for
every feasible common continuation; it need not retain every prefix history.

| Lemma | Statement | Argument / implementation |
|---|---|---|
| L1, cell equivalence | Recognized owner/cell selections have exactly the kernel's unary and pairwise physical compatibility | Individually blocked actions removed; arrangement partitions footprints; predicted conflicts checked against activation compiler. Fixed templates have unary/pairwise collision semantics. |
| L2, unit locality | After all actions of a complete unit, no future action can reuse one of its owners | A future action sharing the owner would belong to the same action/owner incidence component. Owner identity can become external occupancy, never empty. |
| L3, full-action/thin-witness | Witness omission does not remove paid cost, effects or occupancy | Every action's entire effect footprint is reserved before branching over connected profile components. A feasible materialized repair has a root-component witness: each connected supplied component is wholly inside or outside it. |
| L4, state sufficiency | Equal event, occupancy and profile partitions have identical future feasibility | Every future interaction is a live-cell conflict/reuse or a live-boundary connection. Forgotten locations have no future incident event by the complete span schedule. |
| L5, safe forgetting | Expired floors/cells and completed-unit owner names can be forgotten under the stated tests | All incident unit/baseline events have occurred; reject a disappearing non-anchor block. The anchor may absorb all forgotten rooted connectivity. Apply L2 to owners. |
| L6, stable labels | Dominance and representative row order preserve cost/count/ID ties | Future IDs are disjoint from processed IDs. Cost/count add equally under a common continuation. With equal counts, inserting the same disjoint sorted IDs preserves the first differing original ID. |
| L7, product representation | Grouped minimum-label GF(2) row bases preserve every joint rooted completion | Established anchored cut factorization in each layer and tensor product; greedy basis ordered by L6 labels. Group ONLY equal occupancy and selected boundary sets. Existing union-find completion tests are independent of cut construction. |
| L8, reconstruction | Every accepting selection replays to a strict feasible repair, and an optimum has an accepting branch | L1/L3 ensure full paid geometry, rooted witnesses ensure all demands, frozen geometry fixes adjacency. L3 gives an optimum witness; L4--L7 preserve its least-label completion. Replay complete original actions. |

These are project proof arguments, not an independent human proof endorsement.

## Complete pseudocode

```text
RecognizeStrictInstance(I):                                  [L1]
  validate schema, frozen rooms, baseline and physical templates
  compile unavailable actions and pairwise physical conflicts
  cells, action_cells <- BuildOwnedCollisionCells(I)
  reject unless cell conflicts equal compiled conflicts
  units <- BuildActionAssetUnits(available actions, owners)   [L2]
  contract baseline access separately in each floor/profile
  optionally delete components with no demands or possible external edge
  schedule <- BuildFloorEventSchedule(units, baseline spans) [L4,L5]
  return recognized structure and measured p,r,z,L,h

BuildOwnedCollisionCells(I):
  for each floor, arrange all available footprint x/y boundaries
  retain covered positive-area cells; reject cells <= EPS
  assign each action its owners on ALL its actual effect floors

BuildActionAssetUnits(A, owners):
  compute connected components of the bipartite incidence graph
  support(J) <- every footprint and effect endpoint floor of its actions

BuildFloorEventSchedule(J, baseline):
  sort floors by elevation and ID; L <- largest complete support span
  schedule each whole unit and baseline edge at its first endpoint floor
  introduce an L-floor look-ahead window; never split an atomic unit

Solve(I):
  R <- RecognizeStrictInstance(I)
  histories <- {empty occupancy, anchor-only partitions, zero label}
  introduce mandatory targets and actual roots in initial window
  for floor f:
    process baseline edges: skip/take in witness only             [L3]
    for complete unit J starting at f:
      for original action a in J:
        IntroduceAction(a):
          emit skipped history
          UpdatePhysicalOccupancy(a):                           [L1,L3]
            reserve all a's paid cells; reject different/external owners
            allow consistent same-owner reuse; charge full original label
          UpdateProfileWitnesses(a):                            [L3]
            branch over subsets of complete supplied connected components
            glue selected endpoints separately per profile
          ReduceRepresentativePartitions():                     [L6,L7]
            keep least label per identical state
            group by occupancy and selected boundary sets
            retain minimum-label product cut-row basis in each group
      turn all completed-unit owners into external occupancy    [L2]
    ForgetCompletedInterface(f):                               [L5]
      remove floor positions; reject any disappearing non-anchor block
      remove expired cells; introduce next floor's roots/targets
      reduce using the same grouped rule
  if no histories: return infeasible
  return ReconstructAndReplayRepair(least accepting label)       [L8]
```

The implementation reconstructs from the stored sorted original IDs; it does
not need a numerical predecessor path. Paid but unused effects survive in the
ID set, price and occupancy; all effects are materialized again during replay.
No accepting state after exhaustive mathematical enumeration means infeasible.
A raw-state/cut-column cap or timeout means incomplete search, never infeasible.
For an empty target set the empty repair is optimal because costs are nonnegative;
vacuous profile layers may use a canonical harmless room anchor. Source=target
obligations likewise require no new path. Multiple distinct sources in one
profile remain unsupported by this rooted solver.

## Derivation of the bound

There are at most prL non-anchor boundary positions and zL live cells. Between
units a cell has two states. Inside J it has h(J,c)+2 states: empty, external,
or one permitted owner. Thus the occupancy factor is at most (h+2)^(zL).
For selected positions U, the product anchored cut matrix has at most 2^|U|
columns; summing retained basis sizes over optional position sets is at most
3^(prL). An action has at most prL supplied connected components across layers,
so witness branching contributes at most 2^(prL). Explicit cut rows and Gaussian
elimination contribute another 2^O(prL). Even a polynomial power of the resource
factor is absorbed by 2^O(zL log(h+2)). There are polynomially many floor,
baseline-edge and original-action events, giving

`T_rec + 2^O(prL + zL log(h+2)) * poly(B)`.

Every partial action set contains at most m IDs. A common decimal scale has
polynomial bit length in the represented decimal costs; summing m scaled
nonnegative costs adds O(log m) bits to the largest scaled numerator. Sorted
ID storage/comparison uses at most the total input ID length plus polynomial
indices. Exact Decimal operations use sufficient precision (`objective.py`),
so cost/count/identifier label operations contribute polynomial bit work.
CP-SAT has a separate checked int64 coefficient-sum restriction and is not the
implementation used to prove this unrestricted-label mathematical bound.

## Hardness with its exact quantifiers

Decision problem: given a recognized physical-template instance and integer
threshold k, is there a strict feasible original-action selection of cost <=k?
Reduce unweighted Set Cover (universe U, sets S_i, threshold k). Use two floors,
one profile, one source room below and one disjoint target room per element
above. For each incidence e in S_i install an aligned private reserved rectangle
joining the source and that element's target. Action i buys all its incidence
portals for unit cost. Incidence rectangles are pairwise separated; all owners
are private, all actions have valid landings and fit supplied reservations.
Integer/rational coordinates and the number of records are polynomial in the
Set Cover encoding. Selected actions cover every element iff every target is
reachable. Cost is exactly the number of selected sets, so the SAME k applies.

Constants: F=2,p=1,L=2,h=1. Growing parameters: upper-floor components r=|U|,
collision cells z proportional to incidence geometry, and action/asset size.
Subset replay on these rectangles is polynomial, giving NP-completeness for
this finite decision family. Two floors alone therefore do not make arbitrary
physical bundles tractable unless P=NP. This is an inherited coverage reduction;
it proves no ETH/parameter-exponent lower bound, no single-shaft hardness, and
no separation from every treewidth/clique-width/CP-SAT algorithm.
