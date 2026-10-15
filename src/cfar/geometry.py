"""Conservative 2D reserved-interface model; no structural or code certificate."""
from __future__ import annotations

from itertools import combinations
from typing import Any
from contextlib import contextmanager
from contextvars import ContextVar
from functools import lru_cache

from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

from .errors import require
from .schema import Instance

EPS = 1e-8
_MEMOIZE = ContextVar("geometry_memoize", default=True)


def _polygon(points) -> Polygon:
    shape = Polygon(points)
    require(shape.is_valid and shape.area > EPS, "POLYGON", "invalid or empty polygon")
    coords = list(shape.exterior.coords)
    require(all(abs(x1-x2) < EPS or abs(y1-y2) < EPS
                for (x1, y1), (x2, y2) in zip(coords, coords[1:])),
            "ORTHOGONAL", "polygon edges must be axis aligned")
    return shape


_cached_polygon = lru_cache(maxsize=8192)(_polygon)


def polygon(points: list) -> Polygon:
    frozen = tuple(tuple(p) for p in points)
    return _cached_polygon(frozen) if _MEMOIZE.get() else _polygon(frozen)


def _centre_space(points, obstacles, radius):
    interior = polygon(points).buffer(-radius, join_style=2)
    blocked = unary_union([polygon(o).buffer(radius, join_style=2) for o in obstacles])
    return interior.difference(blocked)


_cached_centre_space = lru_cache(maxsize=2048)(_centre_space)


@contextmanager
def geometry_memoization(enabled):
    """Only pure immutable polygons/free-space are cached, never validity results."""
    token = _MEMOIZE.set(bool(enabled))
    try:
        yield
    finally:
        _MEMOIZE.reset(token)


def geometry_cache_info():
    return dict(polygon=_cached_polygon.cache_info()._asdict(), centre_space=_cached_centre_space.cache_info()._asdict())


def clear_geometry_caches():
    _cached_polygon.cache_clear()
    _cached_centre_space.cache_clear()


def room_index(instance: Instance) -> dict[str, tuple[dict, dict]]:
    return {r["room_id"]: (floor, r) for floor in instance["floors"] for r in floor["rooms"]}


def polygons_touch(first: list, second: list) -> bool:
    a, b = polygon(first), polygon(second)
    return a.intersection(b).area <= EPS and a.boundary.intersection(b.boundary).length > EPS


def computed_adjacency(floor: dict) -> set[tuple[str, str]]:
    return {tuple(sorted((a["room_id"], b["room_id"])))
            for a, b in combinations(floor["rooms"], 2)
            if polygons_touch(a["polygon"], b["polygon"])}


def validate_floor_geometry(floor: dict) -> None:
    boundary = polygon(floor["boundary"])
    rooms = [(r["room_id"], polygon(r["polygon"])) for r in floor["rooms"]]
    for rid, shape in rooms:
        require(boundary.covers(shape), "ROOM_CONTAINMENT", rid)
    for (aid, a), (bid, b) in combinations(rooms, 2):
        require(a.intersection(b).area <= EPS, "ROOM_OVERLAP", f"{aid}/{bid}")
    for obstacle in floor["obstacles"]:
        require(boundary.covers(polygon(obstacle)), "OBSTACLE_CONTAINMENT", floor["floor_id"])
    for zone in floor["reserved_portal_zones"]:
        require(boundary.covers(polygon(zone)), "ZONE_CONTAINMENT", floor["floor_id"])


def connection_feasible(instance: Instance, connection: dict, profiles: list[str]) -> dict[str, Any]:
    """Return recomputed evidence, raising a named error on any failed check."""
    rooms = room_index(instance)
    u, v = connection["u"], connection["v"]
    f1, r1 = rooms[u]
    f2, r2 = rooms[v]
    geom = connection["geometry"]
    kind = connection["kind"]
    cid = connection["connection_id"]
    require(set(profiles) <= set(connection["physical_profiles"]), "PHYSICAL_PROFILE", cid)
    specifications = {p["profile_id"]: p for p in instance["profiles"]}
    width = geom["width_m"]
    for pid in profiles:
        p = specifications[pid]
        require(width + EPS >= p["min_width_m"], "PROFILE_WIDTH", f"{cid}/{pid}")
        require(kind != "stair" or p["can_use_stairs"], "PROFILE_STAIRS", f"{cid}/{pid}")
        if kind == "ramp":
            require(geom["rise_m"] / geom["run_m"] <= p["max_slope"] + EPS,
                    "PROFILE_SLOPE", f"{cid}/{pid}")

    landings = {landing["room_id"]: polygon(landing["polygon"]) for landing in geom["landings"]}
    require(set(landings) == {u, v} and len(geom["landings"]) == 2, "LANDING_ENDPOINTS", cid)
    for rid, shape in landings.items():
        floor, room = rooms[rid]
        require(polygon(room["polygon"]).covers(shape), "LANDING_CONTAINMENT", f"{cid}/{rid}")
        require(all(shape.intersection(polygon(o)).area <= EPS for o in floor["obstacles"]),
                "LANDING_OBSTACLE", f"{cid}/{rid}")
        x1, y1, x2, y2 = shape.bounds
        # Landings are rectangular clear patches: bounding-box dimensions alone are insufficient.
        require(abs(shape.area-(x2-x1)*(y2-y1)) <= EPS, "LANDING_RECTANGLE", cid)
        for pid in profiles:
            require(min(x2-x1, y2-y1) + EPS >= specifications[pid]["clearance_m"],
                    "PROFILE_CLEARANCE", f"{cid}/{rid}/{pid}")

    if kind == "door":
        require(f1["floor_id"] == f2["floor_id"], "DOOR_FLOOR", cid)
        opening = LineString(geom["opening"])
        require(opening.length > EPS and abs(opening.length-width) <= EPS, "OPENING_WIDTH", cid)
        (x1, y1), (x2, y2) = geom["opening"]
        require(abs(x1-x2) < EPS or abs(y1-y2) < EPS, "OPENING_ORTHOGONAL", cid)
        shared = polygon(r1["polygon"]).boundary.intersection(polygon(r2["polygon"]).boundary)
        require(shared.buffer(EPS).covers(opening), "DOOR_SHARED_WALL", cid)
        for rid in (u, v):
            require(landings[rid].buffer(EPS).covers(opening), "DOOR_LANDING_CONTACT", f"{cid}/{rid}")
        require(all(opening.intersection(polygon(o)).length <= EPS for o in f1["obstacles"]),
                "DOOR_OBSTACLE", cid)
        occupied = []
    else:
        require(f1["floor_id"] != f2["floor_id"], "PORTAL_FLOORS", cid)
        rise = abs(f1["elevation_m"] - f2["elevation_m"])
        require(abs(geom["rise_m"]-rise) <= EPS and rise > EPS, "PORTAL_RISE", cid)
        footprints = {item["room_id"]: polygon(item["polygon"]) for item in geom["footprints"]}
        require(set(footprints) == {u, v} and len(geom["footprints"]) == 2, "PORTAL_ENDPOINTS", cid)
        require(footprints[u].equals(footprints[v]), "PORTAL_ALIGNMENT", cid)
        occupied = []
        for rid, shape in footprints.items():
            floor, room = rooms[rid]
            require(polygon(room["polygon"]).covers(shape), "PORTAL_CONTAINMENT", f"{cid}/{rid}")
            require(any(polygon(z).covers(shape) for z in floor["reserved_portal_zones"]),
                    "PORTAL_RESERVED_ZONE", f"{cid}/{rid}")
            require(all(shape.intersection(polygon(o)).area <= EPS for o in floor["obstacles"]),
                    "PORTAL_OBSTACLE", f"{cid}/{rid}")
            require(shape.covers(landings[rid]), "PORTAL_LANDING", f"{cid}/{rid}")
            x1, y1, x2, y2 = shape.bounds
            require(abs(shape.area-(x2-x1)*(y2-y1)) <= EPS and min(x2-x1,y2-y1)+EPS >= width,
                    "PORTAL_FOOTPRINT_WIDTH", cid)
            if kind in {"stair","ramp"}:
                require(max(x2-x1,y2-y1)+EPS >= geom["run_m"], "PORTAL_RUN_FOOTPRINT", cid)
            occupied.append({"floor_id": floor["floor_id"], "polygon": list(map(list, shape.exterior.coords))})
    return {"geometry_model": "reserved_interfaces_2d_v1", "connection_id": cid,
            "profiles": sorted(profiles), "checks": ["containment", "clearance", "obstacles", "endpoints", "profiles"],
            "occupied": occupied}


def portal_feasible(instance: Instance, connection: dict, profiles: list[str]) -> dict:
    require(connection["kind"] != "door", "PORTAL_KIND", connection["connection_id"])
    return connection_feasible(instance, connection, profiles)


def connector_feasible(instance: Instance, connection: dict, profiles: list[str]) -> dict:
    return connection_feasible(instance, connection, profiles)


def joint_geometry(instance: Instance, active: dict[str, list[str]], *, metrics=None) -> dict[str, dict]:
    catalog = {c["connection_id"]: c for c in instance["connections"]}
    checks = {cid: connection_feasible(instance, catalog[cid], ps) for cid, ps in sorted(active.items())}
    for (aid, a), (bid, b) in combinations(checks.items(), 2):
        ca, cb = catalog[aid], catalog[bid]
        if ca["kind"] == cb["kind"] == "door":
            fa = room_index(instance)[ca["u"]][0]["floor_id"]
            fb = room_index(instance)[cb["u"]][0]["floor_id"]
            if fa == fb:
                require(LineString(ca["geometry"]["opening"]).intersection(LineString(cb["geometry"]["opening"])).length <= EPS,
                        "DOOR_COLLISION", f"{aid}/{bid}")
        for x in a["occupied"]:
            for y in b["occupied"]:
                if x["floor_id"] == y["floor_id"]:
                    same_asset = (catalog[aid]["kind"] == catalog[bid]["kind"]
                                  and catalog[aid]["geometry"].get("asset_id") == catalog[bid]["geometry"].get("asset_id")
                                  and polygon(x["polygon"]).equals(polygon(y["polygon"])))
                    if same_asset:
                        continue
                    if metrics is not None:
                        metrics["portal_footprint_intersection_tests"] = metrics.get("portal_footprint_intersection_tests",0)+1
                    require(polygon(x["polygon"]).intersection(polygon(y["polygon"])).area <= EPS,
                            "PORTAL_COLLISION", f"{aid}/{bid}")
    # Room nodes abstract continuous motion only when the required profile's free centre-space is connected.
    rooms = room_index(instance)
    specifications = {p["profile_id"]: p for p in instance["profiles"]}
    requested: dict[str, set[str]] = {}
    for cid, ps in active.items():
        for rid in (catalog[cid]["u"], catalog[cid]["v"]):
            requested.setdefault(rid,set()).update(ps)
    for obligation in instance["obligations"]:
        for rid in (obligation["source"],obligation["target"]):
            requested.setdefault(rid,set()).add(obligation["profile_id"])
    room_checks = {}
    for rid, ps in sorted(requested.items()):
        floor, room = rooms[rid]
        for pid in sorted(ps):
            radius = specifications[pid]["min_width_m"]/2
            points = tuple(tuple(p) for p in room["polygon"])
            obstacles = tuple(tuple(tuple(p) for p in o) for o in floor["obstacles"])
            free = (_cached_centre_space(points,obstacles,radius) if _MEMOIZE.get()
                    else _centre_space(points,obstacles,radius))
            require(free.geom_type == "Polygon" and free.area > EPS,
                    "ROOM_PROFILE_CONNECTIVITY", f"{rid}/{pid}")
            for cid, permitted in active.items():
                if pid not in permitted:
                    continue
                for landing in catalog[cid]["geometry"]["landings"]:
                    if landing["room_id"] == rid:
                        centre = polygon(landing["polygon"]).centroid
                        require(free.buffer(EPS).covers(centre), "ROOM_LANDING_ACCESS", f"{cid}/{rid}/{pid}")
            room_checks[f"{rid}/{pid}"] = {"connected":True,"centre_space_area_m2":free.area,
                                            "body_model":"axis_aligned_square","width_m":2*radius}
    return {"connections": checks,"room_accessibility":room_checks,
            "joint_checks":["portal_asset_overlap","door_nonoverlap","connected_profile_room_space"]}
