"""Independent flow optimization on the same recognized strict physical model.

Recognition/geometry are shared with the DP; connectivity and optimization are
not. No owner or purchase vertex is introduced into the route graph.
"""
from collections import defaultdict
from fractions import Fraction
from math import isfinite, lcm
from time import perf_counter

from .actions import apply_actions
from .errors import require
from .geometry import room_index
from .interface_recognition import recognize_physical_interface
from .objective import action_cost
from .obligations import verify_obligations
from .validation import baseline_active


def integer_costs(actions):
    """Scale finite decimal costs without floating point or Decimal rounding."""
    values = [Fraction(str(a["cost"])) for a in actions]
    scale = lcm(*(v.denominator for v in values)) if values else 1
    coefficients = [v.numerator * (scale // v.denominator) for v in values]
    require(all(c >= 0 for c in coefficients) and sum(coefficients) < 2**61,
            "CP_SAT_COST_RANGE", "exact integer cost sum exceeds safe solver range")
    return coefficients, scale


def solve_cp_sat(instance, *, time_limit=60.0, seed=0):
    from ortools.sat.python import cp_model
    import ortools

    require(isfinite(time_limit) and time_limit > 0, "CP_SAT_LIMIT", "positive finite seconds required")
    started = perf_counter()
    recognized = recognize_physical_interface(instance)
    optimization_started = perf_counter()
    model = cp_model.CpModel()
    actions = sorted(instance["actions"], key=lambda a: a["action_id"])
    x = {a["action_id"]: model.new_bool_var("action:" + a["action_id"]) for a in actions}
    for aid in recognized["blocked"]:
        model.add(x[aid] == 0)

    # Full purchased occupancy, including effects unused in any route witness.
    users = defaultdict(list)
    for aid, occupancy in recognized["action_cells"].items():
        for cell, owner in occupancy.items():
            users[owner, cell].append(x[aid])
    by_cell = defaultdict(list)
    for (owner, cell), variables in sorted(users.items()):
        y = model.new_bool_var("usage:" + owner + ":" + cell)
        model.add_max_equality(y, variables)
        by_cell[cell].append(y)
    for variables in by_cell.values():
        model.add(sum(variables) <= 1)

    catalog = {c["connection_id"]: c for c in instance["connections"]}
    baseline = baseline_active(instance)
    rooms = sorted(room_index(instance))
    flow_variables = 0
    for pid, root in sorted(recognized["anchors"].items()):
        targets = {o["target"] for o in instance["obligations"] if o["profile_id"] == pid} - {root}
        demand = len(targets)
        if not demand:
            continue
        suppliers = defaultdict(set)
        for action in actions:
            for effect in action["effects"]:
                if pid in effect["permitted_profiles"]:
                    c = catalog[effect["connection_id"]]
                    suppliers[tuple(sorted((c["u"], c["v"])))].add(action["action_id"])
        fixed = {tuple(sorted((catalog[cid]["u"], catalog[cid]["v"])))
                 for cid, permissions in baseline.items() if pid in permissions}
        balance = defaultdict(list)
        for u, v in sorted(fixed | suppliers.keys()):
            if u == v:
                continue
            if (u, v) in fixed:
                enabled = 1
            else:
                enabled = model.new_bool_var("edge:" + pid + ":" + u + ":" + v)
                model.add_max_equality(enabled, [x[a] for a in sorted(suppliers[u, v])])
            for first, second in ((u, v), (v, u)):
                flow = model.new_int_var(0, demand, "flow:" + pid + ":" + first + ":" + second)
                flow_variables += 1
                model.add(flow <= demand * enabled)
                balance[first].append(flow)
                balance[second].append(-flow)
        for room in rooms:
            supply = demand if room == root else (-1 if room in targets else 0)
            model.add(sum(balance[room]) == supply)

    coefficients, scale = integer_costs(actions)
    cost = sum(c * x[a["action_id"]] for c, a in zip(coefficients, actions))
    count = sum(x.values())
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = seed
    stages = []
    incumbent = None
    failure_status = None
    model_built_at = perf_counter()

    def optimize(expression, maximize=False, objective_name="cost_scaled"):
        nonlocal incumbent, failure_status
        remaining = time_limit - (perf_counter() - started)
        if remaining <= 0:
            failure_status = "limit_exceeded"
            return False
        solver.parameters.max_time_in_seconds = remaining
        if maximize:
            model.maximize(expression)
        else:
            model.minimize(expression)
        status = solver.solve(model)
        stages.append(dict(status=solver.status_name(status), wall_seconds=solver.wall_time,
                           objective_name=objective_name, maximize=maximize,
                           objective_value=solver.objective_value if status in (cp_model.OPTIMAL,cp_model.FEASIBLE) else None,
                           best_bound=solver.best_objective_bound if status in (cp_model.OPTIMAL,cp_model.FEASIBLE,cp_model.UNKNOWN) else None,
                           branches=solver.num_branches, conflicts=solver.num_conflicts))
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            incumbent = sorted(aid for aid, var in x.items() if solver.value(var))
        if status != cp_model.OPTIMAL:
            failure_status = ("infeasible" if status == cp_model.INFEASIBLE else
                              "model_invalid" if status == cp_model.MODEL_INVALID else "limit_exceeded")
            return False
        model.add(expression == solver.value(expression))
        return True

    # Exact cost, cardinality, then lexicographically smallest sorted ID tuple.
    # With cardinality fixed, prefer inclusion of the earliest available ID.
    done = optimize(cost) and optimize(count, objective_name="action_count")
    if done:
        for aid in sorted(x):
            if not optimize(x[aid], maximize=True, objective_name="include:"+aid):
                done = False
                break
    result = dict(method="strict_flow_cp_sat_v1", status="optimal" if done else failure_status,
                  variant="SCFAR", selected=incumbent if done else None,
                  cost=str(action_cost(instance, incumbent)) if done else None,
                  input_fingerprint=recognized["input_fingerprint"], parameters=recognized["parameters"],
                  statistics=dict(stages=stages, flow_variables=flow_variables, cost_scale=scale,
                                  solver_version=ortools.__version__, workers=1,
                                  elapsed_seconds=perf_counter()-started),
                  scope=recognized["scope"],
                  optimality_evidence="CP-SAT OPTIMAL at every lexicographic stage; shared geometry recognizer")
    result["timings"] = dict(recognized["timings"], formulation_seconds=model_built_at-optimization_started,
                            optimization_seconds=perf_counter()-model_built_at,
                            replay_seconds=None)
    result["recognition_counters"] = recognized["counters"]
    result["best_bound"] = None
    result["relative_cost_gap"] = None
    result["bound_precision"] = "unavailable"
    if incumbent is not None and stages and stages[0]["status"] == "OPTIMAL":
        result["best_bound"] = str(action_cost(instance, incumbent))
        result["relative_cost_gap"] = 0.0
        result["bound_precision"] = "exact cost stage; later tie stages may remain unresolved"
    elif stages and stages[0]["best_bound"] is not None and sum(coefficients) <= 2**53:
        # CP-SAT exposes bounds as doubles. Never call these exact certificates.
        bound = stages[0]["best_bound"] / scale
        result["best_bound"] = str(bound)
        result["bound_precision"] = "solver-reported floating estimate in original cost units"
        if incumbent is not None:
            upper = float(action_cost(instance, incumbent))
            result["relative_cost_gap"] = max(0.0, upper-bound)/max(1.0,abs(upper))
    if incumbent is not None and result["status"] != "infeasible":
        replay_started = perf_counter()
        repair = apply_actions(instance, incumbent)
        verification = verify_obligations(repair["instance"], repair["active"])
        require(verification["satisfied"], "CP_SAT_INTERNAL_REPLAY", "flow selection failed materialization")
        result.update(reachability=verification, geometry=repair["geometry"], adjacency=repair["adjacency"])
        if not done:
            result["incumbent"] = dict(selected=incumbent, cost=str(action_cost(instance, incumbent)))
        result["timings"]["replay_seconds"] = perf_counter()-replay_started
    return result
