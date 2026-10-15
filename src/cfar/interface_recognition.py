"""Conservative M09 recognizer; no compressed solver or novelty certificate."""
from itertools import combinations
from time import perf_counter

from shapely.geometry import box

from .conflict_compilation import compile_activation_constraints
from .errors import require
from .geometry import EPS, polygon, room_index
from .io import fingerprint
from .validation import baseline_active, validate_instance


def recognize_physical_interface(instance: dict, *, prune_irrelevant: bool = False) -> dict:
    started = perf_counter()
    validate_instance(instance)
    validated_at = perf_counter()
    actions = sorted(instance["actions"], key=lambda a: a["action_id"])
    require(all(a["type"] == "physical_intervention" and not a["requires"] and not a["excludes"]
                and all(e["op"] == "activate_connection" and e["permitted_profiles"] for e in a["effects"])
                for a in actions), "INTERFACE_SCOPE", "independent physical activation actions required")
    catalog = {c["connection_id"]: c for c in instance["connections"]}
    used = {e["connection_id"] for a in actions for e in a["effects"]}
    require(all(catalog[cid]["kind"] != "door" for cid in used),
            "INTERFACE_SCOPE", "candidate doors need a different collision representation")
    existing_assets = {c["geometry"].get("asset_id") for c in catalog.values() if c["existing"]}
    require(all(catalog[cid]["geometry"]["asset_id"] not in existing_assets for cid in used),
            "INTERFACE_BACKGROUND_ASSET", "new assets must be disjoint from existing identities")
    floors = sorted(instance["floors"], key=lambda f: (f["elevation_m"], f["floor_id"]))
    require(len({f["elevation_m"] for f in floors}) == len(floors),
            "INTERFACE_FLOOR_ORDER", "distinct elevations required")
    ranks = {f["floor_id"]: i for i, f in enumerate(floors)}
    rooms = room_index(instance)
    room_floor = {rid: floor["floor_id"] for rid, (floor, _) in rooms.items()}
    profiles = sorted(p["profile_id"] for p in instance["profiles"])
    anchors = {}
    for pid in profiles:
        sources = {o["source"] for o in instance["obligations"] if o["profile_id"] == pid}
        require(len(sources) <= 1, "INTERFACE_ROOTED", f"at most one obligation source required for {pid}")
        # A vacuous layer uses a harmless canonical room as its anchor.
        anchors[pid] = next(iter(sources)) if sources else min(rooms)
    constraints = compile_activation_constraints(instance, max_actions=len(actions))
    compiled_at = perf_counter()
    available = [a for a in actions if a["action_id"] not in constraints["blocked"]]
    ownership, support, shapes = {}, {}, {f["floor_id"]: {} for f in floors}
    for action in available:
        aid = action["action_id"]
        ownership[aid], support[aid] = set(), set()
        for effect in action["effects"]:
            c = catalog[effect["connection_id"]]
            owner = c["geometry"]["asset_id"]
            ownership[aid].add(owner)
            support[aid].update(room_floor[rid] for rid in (c["u"], c["v"]))
            for record in c["geometry"]["footprints"]:
                fid = room_floor[record["room_id"]]
                shape = polygon(record["polygon"])
                require(shape.equals(box(*shape.bounds)), "INTERFACE_RECTANGLE", owner)
                shapes[fid][owner] = shape
                support[aid].add(fid)
    cells_started = perf_counter()
    cells = []
    coverage_tests = 0
    for floor in floors:
        fid = floor["floor_id"]
        local = shapes[fid]
        xs = sorted({x for s in local.values() for x in (s.bounds[0], s.bounds[2])})
        ys = sorted({y for s in local.values() for y in (s.bounds[1], s.bounds[3])})
        for x1, x2 in zip(xs, xs[1:]):
            for y1, y2 in zip(ys, ys[1:]):
                cell = box(x1, y1, x2, y2)
                coverage_tests += len(local)
                owners = sorted(owner for owner, s in local.items() if s.covers(cell))
                if not owners:
                    continue
                require(cell.area > EPS, "INTERFACE_CELL_EPS", f"{fid}/{cell.bounds}")
                cid = f"cell{len(cells):06d}"
                cells.append(dict(cell_id=cid, floor_id=fid, bounds=list(cell.bounds), asset_ids=owners))
    cells_finished = perf_counter()
    # Use each action's actual touched floors, not every floor of a shared owner's catalogue.
    action_cells = {a["action_id"]: {} for a in available}
    for action in available:
        aid = action["action_id"]
        for effect in action["effects"]:
            c = catalog[effect["connection_id"]]
            owner = c["geometry"]["asset_id"]
            touched = {room_floor[r["room_id"]] for r in c["geometry"]["footprints"]}
            for cell in cells:
                if cell["floor_id"] in touched and owner in cell["asset_ids"]:
                    action_cells[aid][cell["cell_id"]] = owner
    predicted = set()
    for a, b in combinations(sorted(action_cells), 2):
        if any(action_cells[a][cid] != action_cells[b][cid]
               for cid in action_cells[a].keys() & action_cells[b].keys()):
            predicted.add((a, b))
    observed = {tuple(c["actions"]) for c in constraints["geometry_conflicts"]}
    require(predicted == observed, "INTERFACE_COLLISION_EQUIVALENCE",
            "cell ownership must match the geometry compiler exactly")
    remaining = set(ownership)
    units = []
    while remaining:
        members = {min(remaining)}
        owners = set(ownership[next(iter(members))])
        while True:
            additions = {aid for aid in remaining - members if ownership[aid] & owners}
            if not additions:
                break
            members.update(additions)
            owners.update(owner for aid in additions for owner in ownership[aid])
        remaining -= members
        touched = {fid for aid in members for fid in support[aid]}
        indices = [ranks[fid] for fid in touched]
        units.append(dict(action_ids=sorted(members), asset_ids=sorted(owners),
                          floor_ids=sorted(touched, key=ranks.get),
                          first_floor=min(indices), last_floor=max(indices),
                          span=max(indices)-min(indices)+1))
    units.sort(key=lambda u: (u["first_floor"], u["action_ids"]))
    baseline = baseline_active(instance)
    components, baseline_span = {}, 1
    for pid in profiles:
        parent = {rid: rid for rid in rooms}

        def find(rid):
            while parent[rid] != rid:
                parent[rid] = parent[parent[rid]]
                rid = parent[rid]
            return rid

        for cid, permitted in baseline.items():
            if pid not in permitted:
                continue
            c = catalog[cid]
            u, v = c["u"], c["v"]
            if room_floor[u] == room_floor[v]:
                parent[find(u)] = find(v)
            else:
                baseline_span = max(baseline_span, abs(ranks[room_floor[u]]-ranks[room_floor[v]])+1)
        components[pid] = {rid: find(rid) for rid in sorted(rooms)}
    all_component_r = max((len({components[pid][rid] for rid in rooms if room_floor[rid] == f["floor_id"]})
             for pid in profiles for f in floors), default=0)
    if prune_irrelevant:
        for pid in profiles:
            marked = {anchors[pid]} | {o["target"] for o in instance["obligations"] if o["profile_id"] == pid}
            for cid, permitted in baseline.items():
                c = catalog[cid]
                if pid in permitted and room_floor[c["u"]] != room_floor[c["v"]]:
                    marked.update((c["u"], c["v"]))
            for action in available:
                for effect in action["effects"]:
                    if pid in effect["permitted_profiles"]:
                        c = catalog[effect["connection_id"]]
                        marked.update((c["u"], c["v"]))
            keep = {components[pid][rid] for rid in marked}
            components[pid] = {rid: component for rid, component in components[pid].items() if component in keep}
    r = max((len({component for rid, component in components[pid].items()
                  if room_floor[rid] == f["floor_id"]}) for pid in profiles for f in floors), default=0)
    z = max((sum(c["floor_id"] == f["floor_id"] for c in cells) for f in floors), default=0)
    parameters = dict(p=len(profiles), r=r, z=z,
                      L=max([baseline_span] + [u["span"] for u in units]),
                      g=max((len(u["asset_ids"]) for u in units), default=0))
    h = 0
    for unit in units:
        owners = set(unit["asset_ids"])
        counts = {c["cell_id"]: len(owners & set(c["asset_ids"])) for c in cells
                  if unit["first_floor"] <= ranks[c["floor_id"]] < unit["first_floor"]+parameters["L"]}
        unit["cell_owner_counts"] = counts
        bound = 1
        for count in counts.values():
            bound *= count+2
        unit["resource_state_upper_bound"] = bound
        h = max([h] + list(counts.values()))
    parameters["h"] = h
    timings = dict(input_validation_seconds=validated_at-started,
                   activation_geometry_seconds=compiled_at-validated_at,
                   footprint_preparation_seconds=cells_started-compiled_at,
                   collision_cell_construction_seconds=cells_finished-cells_started,
                   unit_and_component_construction_seconds=perf_counter()-cells_finished)
    timings["recognition_seconds"] = perf_counter()-started
    return dict(format="physical_interface_recognition_v1", input_fingerprint=fingerprint(instance),
                recognized=True, parameters=parameters, floor_order=[f["floor_id"] for f in floors],
                anchors=anchors, components=components, cells=cells, units=units,
                action_cells=action_cells, blocked=constraints["blocked"],
                all_component_r=all_component_r, prune_irrelevant=prune_irrelevant,
                timings=timings,
                counters=dict(cell_coverage_tests=coverage_tests, generated_cells=len(cells),
                              compilation_portal_footprint_intersection_tests=constraints["geometry_metrics"]["portal_footprint_intersection_tests"],
                              geometry_compilation_calls=constraints["geometry_calls_after_validation"],
                              geometry_compilation_requests=constraints["geometry_requests"]),
                geometry_conflicts=constraints["geometry_conflicts"],
                scope="M09 rectangular physical activations; " +
                      ("marked-component r" if prune_irrelevant else "conservative all-component r") + "; not M10 background",
                witness_status="recognition only; no feasibility or optimality conclusion")
