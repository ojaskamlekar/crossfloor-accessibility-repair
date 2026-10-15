"""Small independent selected-set checks, not a second general geometry engine.

No cfar geometry, graphs, action application, cells or recognizer is imported.
The rectangle check uses coordinate intervals on the recognized template class;
it does not certify containment, clearances, obstacles or statutory compliance.
"""
from itertools import combinations


def check_selection(instance, selected):
    selected=set(selected)
    room_floor={r["room_id"]:f["floor_id"]for f in instance["floors"]for r in f["rooms"]}
    catalog={c["connection_id"]:c for c in instance["connections"]}
    active={}
    for floor in instance["floors"]:
        for edge in floor["access_edges"]:
            active.setdefault(edge["connection_id"],set()).update(edge["permitted_profiles"])
    for portal in instance["portals"]:
        for edge in portal["transitions"]:
            active.setdefault(edge["connection_id"],set()).update(edge["permitted_profiles"])
    paid=[]
    for action in instance["actions"]:
        if action["action_id"]not in selected:continue
        for effect in action["effects"]:
            if effect["op"]!="activate_connection":raise ValueError("activation-only independent check")
            cid=effect["connection_id"]
            active.setdefault(cid,set()).update(effect["permitted_profiles"])
            c=catalog[cid]
            if action["type"]=="physical_intervention":
                for patch in c["geometry"].get("footprints",[]):
                    pts=patch["polygon"]
                    bounds=(min(p[0]for p in pts),min(p[1]for p in pts),max(p[0]for p in pts),max(p[1]for p in pts))
                    paid.append((room_floor[patch["room_id"]],c["geometry"]["asset_id"],bounds))
    collisions=[]
    for a,b in combinations(paid,2):
        if a[0]!=b[0] or a[1]==b[1]:continue
        x=max(0,min(a[2][2],b[2][2])-max(a[2][0],b[2][0]))
        y=max(0,min(a[2][3],b[2][3])-max(a[2][1],b[2][1]))
        if x*y>1e-8:collisions.append((a[0],a[1],b[1]))
    outcomes=[]
    for obligation in instance["obligations"]:
        pid=obligation["profile_id"]; graph={r:set()for r in room_floor}
        for cid,profiles in active.items():
            if pid in profiles:
                c=catalog[cid];graph[c["u"]].add(c["v"]);graph[c["v"]].add(c["u"])
        seen={obligation["source"]};stack=list(seen)
        while stack:
            for nxt in graph[stack.pop()]-seen:seen.add(nxt);stack.append(nxt)
        outcomes.append(obligation["target"]in seen)
    return dict(paid_footprints_compatible=not collisions,collisions=collisions,
                obligations_satisfied=all(outcomes),obligation_results=outcomes,
                scope="independent paid rectangle overlap and graph reachability; full geometry replay still required")
