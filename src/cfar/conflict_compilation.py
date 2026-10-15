"""Unary/pairwise compilation for fixed-geometry strict activation selections.

No reachability solver; proof and scope in docs/geometry_conflict_compilation.md.
"""
from __future__ import annotations

from copy import deepcopy
from itertools import combinations

from .errors import ValidationError, require
from .geometry import joint_geometry
from .io import fingerprint
from .validation import baseline_active, validate_instance


def compile_activation_constraints(instance: dict, max_actions: int = 100) -> dict:
    validate_instance(instance)
    actions = sorted(instance["actions"], key=lambda a: a["action_id"])
    require(len(actions) <= max_actions, "CONFLICT_ACTION_LIMIT", f"{len(actions)} > {max_actions}")
    require(all(e["op"] == "activate_connection" for a in actions for e in a["effects"]),
            "CONFLICT_SCOPE", "only fixed-geometry activations supported")
    baseline = baseline_active(instance)
    checks = 0
    requests = 0
    cache = {}
    metrics = {"portal_footprint_intersection_tests":0}

    def test(selected):
        nonlocal checks, requests
        requests += 1
        active = deepcopy(baseline)
        for action in selected:
            for effect in action["effects"]:
                cid = effect["connection_id"]
                active[cid] = sorted(set(active.get(cid, [])) | set(effect["permitted_profiles"]))
        signature = tuple((cid, tuple(sorted(permitted))) for cid, permitted in sorted(active.items()))
        if signature in cache:
            return cache[signature]
        checks += 1
        try:
            joint_geometry(instance, active, metrics=metrics)
        except ValidationError as error:
            cache[signature] = {"code": error.code, "detail": str(error)}
        else:
            cache[signature] = None
        return cache[signature]

    # Validation already checks B; report actual additional compilation calls.
    blocked, available = {}, []
    for action in actions:
        failure = test([action])
        if failure is not None:
            blocked[action["action_id"]] = failure
        else:
            available.append(action)
    conflicts = []
    for first, second in combinations(available, 2):
        failure = test([first, second])
        if failure is not None:
            conflicts.append({"actions": [first["action_id"], second["action_id"]], **failure})
    exclusions = sorted({tuple(sorted((a["action_id"], other))) for a in actions for other in a["excludes"]})
    return {"format": "fixed_activation_constraints_v1", "input_fingerprint": fingerprint(instance),
            "action_ids": [a["action_id"] for a in actions], "blocked": blocked, "geometry_conflicts": conflicts,
            "requires": {a["action_id"]: sorted(a["requires"]) for a in actions},
            "excludes": [list(pair) for pair in exclusions], "geometry_calls_after_validation": checks,
            "geometry_requests": requests, "geometry_cache_hits": requests-checks,
            "geometry_metrics": metrics,
            "scope": "reserved_interfaces_2d_v1 fixed-room strict activations; reachability not evaluated"}


def selection_admissibility(compiled: dict, selected: list[str]) -> dict:
    require(len(selected) == len(set(selected)), "DUPLICATE_SELECTION", str(selected))
    choices = set(selected)
    require(choices <= set(compiled["action_ids"]), "UNKNOWN_SELECTION", str(choices))
    violations = []
    for aid in sorted(choices):
        if aid in compiled["blocked"]:
            violations.append({"code": compiled["blocked"][aid]["code"], "actions": [aid]})
        missing = set(compiled["requires"][aid])-choices
        if missing:
            violations.append({"code": "ACTION_REQUIRES", "actions": [aid], "missing": sorted(missing)})
    for conflict in compiled["geometry_conflicts"]:
        if set(conflict["actions"]) <= choices:
            violations.append({"code": conflict["code"], "actions": conflict["actions"]})
    for pair in compiled["excludes"]:
        if set(pair) <= choices:
            violations.append({"code": "ACTION_EXCLUDES", "actions": pair})
    return {"admissible": not violations, "violations": violations}
