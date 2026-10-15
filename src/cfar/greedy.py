"""Whole-action greedy comparator; a failed heuristic is never infeasibility."""
from fractions import Fraction
from itertools import combinations, chain

from .actions import apply_actions
from .graphs import build_profile_graph
from .interface_recognition import recognize_physical_interface
from .objective import action_cost
from .obligations import verify_obligations
from .errors import ValidationError, require


def _reach(instance, active, anchors):
    reached = set()
    for pid, root in sorted(anchors.items()):
        graph = build_profile_graph(instance, pid, active)
        stack, seen = [root], {root}
        while stack:
            for other in graph[stack.pop()] - seen:
                seen.add(other)
                stack.append(other)
        reached.update((pid, room) for room in seen)
    return reached


def solve_greedy(instance):
    recognized = recognize_physical_interface(instance)
    actions = {a["action_id"]: a for a in instance["actions"]}
    selected, occupancy = [], {}
    while True:
        repair = apply_actions(instance, selected)
        verification = verify_obligations(repair["instance"], repair["active"])
        if verification["satisfied"]:
            return dict(method="whole_action_greedy_v1", status="feasible", selected=selected,
                        cost=str(action_cost(instance, selected)), input_fingerprint=recognized["input_fingerprint"],
                        reachability=verification, geometry=repair["geometry"], adjacency=repair["adjacency"])
        before = _reach(instance, repair["active"], recognized["anchors"])
        candidates = []
        for aid, cells in recognized["action_cells"].items():
            if aid in selected or any(c in occupancy and occupancy[c] != owner for c, owner in cells.items()):
                continue
            trial = apply_actions(instance, sorted(selected + [aid]))
            gain = len(_reach(instance, trial["active"], recognized["anchors"]) - before)
            if gain:
                candidates.append((Fraction(str(actions[aid]["cost"])) / gain, aid))
        if not candidates:
            return dict(method="whole_action_greedy_v1", status="heuristic_failed", selected=None, cost=None,
                        partial_selected=selected, input_fingerprint=recognized["input_fingerprint"])
        aid = min(candidates)[1]
        selected = sorted(selected + [aid])
        occupancy.update(recognized["action_cells"][aid])


def improve_greedy(instance, *, exchange_budget=256):
    """Greedy plus deletion and bounded 0..2-out/0..2-in exchanges.

    Every candidate is a complete original action set and is physically replayed.
    The deterministic budget counts all exchange candidates, including invalid
    and nonimproving ones. A failed construction can be rescued by an exchange;
    exhausting this neighborhood is never an infeasibility certificate.
    """
    require(type(exchange_budget) is int and exchange_budget >= 0,
            "GREEDY_BUDGET", "nonnegative integer exchange budget required")
    base = solve_greedy(instance)
    chosen = base.get("selected") or base.get("partial_selected", [])
    ids = sorted(a["action_id"] for a in instance["actions"])
    stats = dict(exchange_budget=exchange_budget, exchange_candidates=0,
                 deletion_candidates=0, removed_redundant_actions=0,
                 construction_status=base["status"], construction_cost=base.get("cost"))

    def label(selected):
        return action_cost(instance, selected), len(selected), tuple(sorted(selected))

    def replay(selected):
        try:
            repair = apply_actions(instance, sorted(selected))
            check = verify_obligations(repair["instance"], repair["active"])
            return (repair, check) if check["satisfied"] else None
        except ValidationError:
            return None

    feasible = replay(chosen)
    # Deletions terminate in at most |A| successful passes; each pass <= |A| tests.
    if feasible:
        changed = True
        while changed:
            changed = False
            for aid in sorted(chosen, key=lambda a: (action_cost(instance, [a]), a), reverse=True):
                trial = sorted(set(chosen)-{aid})
                stats["deletion_candidates"] += 1
                check = replay(trial)
                if check:
                    chosen, feasible, changed = trial, check, True
                    stats["removed_redundant_actions"] += 1
                    break
    start = list(chosen)
    outside = sorted(set(ids)-set(start), key=lambda a: (action_cost(instance, [a]), a))
    removals = list(chain.from_iterable(combinations(start, k) for k in range(min(2,len(start))+1)))
    removals.sort(key=lambda s: (-action_cost(instance, s), tuple(s)))
    best_label = label(chosen) if feasible else None
    # One bounded neighborhood of the pruned starting set, not unbounded descent.
    for removed in removals:
        additions = chain.from_iterable(combinations(outside, k) for k in range(min(2,len(outside))+1))
        for added in additions:
            if stats["exchange_candidates"] >= exchange_budget:
                break
            stats["exchange_candidates"] += 1
            candidate = sorted((set(start)-set(removed)) | set(added))
            candidate_label = label(candidate)
            if best_label is not None and candidate_label >= best_label:
                continue
            check = replay(candidate)
            if check:
                chosen, feasible, best_label = candidate, check, candidate_label
        if stats["exchange_candidates"] >= exchange_budget:
            break
    result = dict(method="whole_action_greedy_exchange_v1", status="feasible" if feasible else "heuristic_failed",
                  selected=chosen if feasible else None, cost=str(action_cost(instance, chosen)) if feasible else None,
                  input_fingerprint=base["input_fingerprint"], statistics=stats)
    if feasible:
        repair, check = feasible
        result.update(reachability=check, geometry=repair["geometry"], adjacency=repair["adjacency"])
    else:
        result["partial_selected"] = start
    return result
