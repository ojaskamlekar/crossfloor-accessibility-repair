"""Declared structural probes, never independent buildings or sampled BIMs."""
from copy import deepcopy
from itertools import combinations
import random

from .interface_scenarios import dense_alternative_probe, coupled_owner_probe
from .physical_set_cover import make_physical_set_cover
from .synthetic_shaft import make_shaft_instance
from .synthetic_star import rectangle
from .geometry import computed_adjacency


FAMILY_EFFECTS = {
    "catalogue": "action count grows; p,r,z,L,h remain fixed (private colliding alternatives)",
    "connectivity": "r and live terminals grow; p=1,h=1,L=2; z also grows (not a pure r intervention)",
    "profiles": "p grows with identical geometry and one action; per-profile connectivity is replicated",
    "ownership": "h grows inside one coupled unit; p,r,z,L remain fixed",
    "support": "one action spans more floors; p,r,z,h stay fixed, L grows",
    "compression": "complete cyclic effect graph grows; more compatible partitions, L also grows",
    "compression-unfavorable": "same bounded interface, dominated alternatives; little partition diversity",
    "pruning": "irrelevant isolated rooms increase unmarked r without changing candidate endpoints or routes",
}


def generate_instance(family, size, seed=0, settings=None):
    if family not in FAMILY_EFFECTS or type(size) is not int or size < 1:
        raise ValueError("known family and positive integer size required")
    settings = settings or {}
    rng = random.Random(seed)
    if family == "pruning":
        instance=make_shaft_instance(1,[(0,0,1)],[1],profiles=1,physical=True)
        for f in instance["floors"]:
            f["boundary"]=rectangle(0,0,6+2*size,4)
            for i in range(size):f["rooms"].append(dict(room_id=f"unused-{f['floor_id']}-{i}",label="irrelevant",
                polygon=rectangle(5+2*i,.5,6+2*i,1.5)))
    elif family in {"catalogue", "compression-unfavorable"}:
        instance = dense_alternative_probe(size)
    elif family == "ownership":
        instance = coupled_owner_probe(size)
    elif family == "connectivity":
        instance = make_physical_set_cover(size, [[i] for i in range(size)])
    elif family == "profiles":
        instance = make_shaft_instance(1,[(0,0,size)],[1],profiles=size,physical=True)
    elif family == "support":
        instance = make_shaft_instance(size,[(0,size-1,1)],[1],profiles=1,physical=True)
    else:
        n = max(2,size)
        instance = make_shaft_instance(n-1,[(0,n-2,1)],[1],profiles=1,physical=True)
        template_c, template_a = instance["connections"][0], instance["actions"][0]
        connections, actions = [], []
        for i,(u,v) in enumerate(combinations(range(n),2)):
            c,a = deepcopy(template_c),deepcopy(template_a)
            cid=f"E{i:04d}"
            c.update(connection_id=cid,evidence_id="e"+cid,u=f"R{u}",v=f"R{v}")
            c["geometry"]["rise_m"]=3*(v-u)
            for field in ("landings","footprints"):
                for record,room in zip(c["geometry"][field],(u,v)):
                    record["room_id"]=f"R{room}"
            a.update(action_id=f"A{i:04d}",cost=rng.randint(1,3),evidence_ids=["e"+cid],
                effects=[dict(op="activate_connection",connection_id=cid,permitted_profiles=["profile0"])])
            a["geometry_certificate"]["connection_ids"]=[cid]
            connections.append(c);actions.append(a)
        instance.update(connections=connections,actions=actions)
    if settings.get("cost_jitter"):
        for action in instance["actions"]:
            action["cost"] = int(action["cost"])*10+rng.randrange(3)
    instance["building_id"]=f"authored-{family}-{size}-seed{seed}"
    instance["description"]="Authored diagnostic family: "+FAMILY_EFFECTS[family]+"; no source-building count."
    return instance


def diagnostic_example():
    """Six rooms, two profiles, disconnected bundle and full paid occupancy."""
    pids=["p0","p1"]
    floors=[];connections=[]
    for f in range(3):
        floor=dict(floor_id=f"F{f}",elevation_m=3*f,boundary=rectangle(0,0,8,4),
            rooms=[dict(room_id=f"{s}{f}",label=f"{s}{f}",polygon=rectangle(x,0,x+4,4)) for s,x in (("L",0),("R",4))],
            access_edges=[],adjacency_edges=[],obstacles=[],reserved_portal_zones=[rectangle(0,0,8,4)])
        floor["adjacency_edges"]=[list(e) for e in sorted(computed_adjacency(floor))]
        cid=f"D{f}"
        connections.append(dict(connection_id=cid,evidence_id="e"+cid,u=f"L{f}",v=f"R{f}",
            kind="door",existing=True,physical_profiles=pids,
            geometry=dict(width_m=1,opening=[[4,1],[4,2]],landings=[
                dict(room_id=f"L{f}",polygon=rectangle(3,1,4,2)),dict(room_id=f"R{f}",polygon=rectangle(4,1,5,2))])))
        floor["access_edges"]=[dict(edge_id=cid,connection_id=cid,permitted_profiles=pids if f!=1 else pids[:1])]
        floors.append(floor)
    for cid,u,v,owner,shape in [
        ("a","L0","L1","left",rectangle(.5,.5,1.5,1.5)),
        ("b","L1","L2","left",rectangle(.5,.5,1.5,1.5)),
        ("u","R1","R2","right",rectangle(5.5,.5,6.5,1.5)),
        ("v","R0","R1","competing-right",rectangle(5.5,.5,6.5,1.5)),
        ("w","R0","R1","escape",rectangle(6.5,2.5,7.5,3.5))]:
        records=[dict(room_id=rid,polygon=shape)for rid in(u,v)]
        connections.append(dict(connection_id=cid,evidence_id="e"+cid,u=u,v=v,kind="lift",existing=False,
            physical_profiles=pids,geometry=dict(asset_id=owner,width_m=1,rise_m=3,run_m=1,landings=records,footprints=records)))
    actions=[]
    for aid,cids,cost in (("A",["a","u"],1),("B",["b"],1),("C",["v"],.5),("D",["w"],3)):
        actions.append(dict(action_id=aid,type="physical_intervention",cost=cost,requires=[],excludes=[],
            effects=[dict(op="activate_connection",connection_id=cid,permitted_profiles=pids)for cid in cids],
            evidence_ids=["e"+cid for cid in cids],geometry_certificate=dict(geometry_model="reserved_interfaces_2d_v1",connection_ids=cids,changed_floor_ids=[])))
    return dict(schema_version="0.1.0",building_id="authored-complete-diagnostic",description="Authored explanatory instance, not BIM evidence.",
        floors=floors,connections=connections,actions=actions,portals=[],original_restoration_actions=[],
        profiles=[dict(profile_id=pid,min_width_m=.4,clearance_m=.4,can_use_stairs=False,max_slope=.1)for pid in pids],
        obligations=[dict(obligation_id=f"O{q}{i}",source="L0",target=t,profile_id=pid)for q,pid in enumerate(pids)for i,t in enumerate(("L1","R2"))])
