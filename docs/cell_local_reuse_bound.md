# Additional structural result: cell-local owner lifetimes

This is a project correctness argument for a more useful sweep, supported by thirty focused implementation tests;
executed comparisons and independent proof review remain pending. It is not a literature
priority claim. The rank-based algebra and last-use resource-state idea are
established techniques; the proposed result concerns their precise transfer to
the full paid-action contract.

## Why complete global units can be unnecessarily restrictive

Consider F floors with one room on each floor and F-1 independent adjacent-floor
lift activations, all referring to one consistent proposed
shaft owner. Each new action touches two floors, but their global action/owner
incidence unit spans all F. The original solver therefore has L_unit=F even
though physical reuse between consecutive actions occurs only on their shared
landing floor. This is a limitation of the complete-unit ownership-erasure
schedule, not a proof that all exact algorithms need a whole-building window.

## Supplied class, constructed order and parameters

Keep the same recognized fixed-template input class. Let L_a be the maximum
consecutive-floor span of an **individual full action** or active baseline
cross-floor edge, at least one. Sort original available actions by earliest
touched floor and original ID, preserving each complete action. Every paid
effect and footprint contributes to that support, including disconnected and
witness-unused effects. Process actions at their earliest support floor.

For each owner/cell pair (o,c), let first(o,c),last(o,c) be the first/last action
indices in this fixed order whose complete footprints use o on c. These are
constructed from the whole available catalogue, not inferred from the selected
solution. Let kappa be the maximum, over action index e and cell c, of the number
of such owner intervals satisfying first(o,c)<=e<=last(o,c). Inclusive intervals
account for the currently introduced action. It is the overlap of **per-cell
owner-use intervals**, not owner count, global unit size, or number of actions.

The original p,r,z retain their meanings. Recognition still constructs/checks
all physical cells and pair conflicts; it additionally computes action support,
the fixed order and owner intervals in polynomial time. The old L_unit and h
are retained as diagnostic measurements; they are not silently relabelled L_a.

## Exact expiration rule

Store every paid live cell as empty, external, or owner:o. When considering an
action, only an empty cell or the same still-recorded owner can be used. Different
owners and external occupancy conflict. After processing action e, replace
owner:o by external on cell c iff last(o,c)<=e. Never replace occupancy by empty.
When the floor expires, drop its cells normally. Do NOT erase all names merely
because a singleton action has finished. A later action on another floor using
the same global owner needs no old-floor name if it cannot touch that cell.

### Cell-local expiration lemma

After the last available action using (o,c), every future action either avoids
c or uses a different owner there. Both owner:o and external then allow exactly
the same future selections. Earlier erasure is unsound when a future action
needs legitimate same-owner reuse. Names therefore need not survive global
action/owner connectivity: they survive precisely through their per-cell last
use. Expiration preserves all purchased footprints, costs and graph effects.

### Window lemma

All effect endpoints and physical cells of an action processed at floor f lie
in the next L_a consecutive floors. A later action beginning after f cannot
touch an expired floor, by definition of its earliest support. The same is true
of baseline events. Thus an L_a-floor look-ahead window is sufficient; global
shaft identity does not increase the window on its own.

### State, correctness and bound

Use the original separate profile partitions, mandatory targets and permanent
anchors; branch over whole supplied graph components only after reserving every
paid cell and charging the complete original label. Forget closed non-anchor
blocks exactly as before. Identical-state dominance and representative bases
group by full occupancy and selected boundary sets.

At event e, a retained owner name on c must belong to an interval covering e;
there are at most kappa possible names. Empty and external add two statuses.
At most z*L_a cells and p*r*L_a component positions are live. The same thin-witness
and continuation argument therefore gives the scoped exact bit-complexity bound

`T_rec + 2^O(p*r*L_a + z*L_a*log(kappa+2)) * poly(B)`.

Soundness: accepting partitions give required routes in the full selected
materialization; cells preserve the compiler's exact compatibility and expiry
cannot remove a future distinction by the expiration lemma. Completeness: take
an optimum action set and its profile root-component witnesses; every whole
action appears at the constructed earliest-support event and its full geometry
fits the window. This branch is not rejected by correct occupancy or forgetting.
Owner expiration preserves its continuations, and minimum-label product bases
preserve its least accepting completion. Exact cost/count/original-ID stability
is unchanged. Infeasible, empty-demand and operational cap cases retain their
original meanings. Numerical recognition remains the same finite 2D kernel.

## Separating families and limits

- Continuous shaft, independent adjacent-floor actions: L_unit=F but L_a=2 and
  kappa=1. With bounded p,r,z the new exponential factor is independent of F.
  Every vertical cut has a unique supplying action, so the analytical optimum
  purchases all F-1 original actions. This is an authored structural family.
- Private colliding alternatives: each owner/cell interval is a single event,
  so kappa=1 regardless of catalogue size. Its name expires immediately, while
  external occupancy still blocks later competitors.
- Coupled-owner bridge family: owner i has one early action and one later
  action using the same cell. These intervals overlap, so kappa grows with the
  genuinely competing reusable owners. The parameter does not hide that cost.
- A disconnected atomic bundle spanning three floors still has L_a>=3. The
  new sweep never reduces support to its chosen witness or breaks a price.

The bound depends on the constructed action order. Alternative orders require
recomputing intervals; the present implementation rejects an unrecognized
reverse schedule rather than applying stale last-use indices. This parameter
is not automatically bounded in every BIM. The old complete-unit and new
cell-local sweeps offer different sufficient structural regimes; no universal
dominance, optimal exponent, new algebraic primitive or broad priority is claimed.
