"""Multi-room subsets from pinned audits; access annotations are hypothetical.

Preserves exact IFC-derived rings/GlobalIds; never closes wall gaps or infers
that a shared boundary is an existing door. All annotated doors, profiles,
reservations, prices and new lifts below are experimental declarations.
"""
import argparse
from copy import deepcopy
import hashlib
from itertools import combinations, product
import json
from math import ceil,floor
from pathlib import Path

from shapely.geometry import Polygon,box
from shapely.ops import unary_union

from cfar.geometry import computed_adjacency
from cfar.interface_recognition import recognize_physical_interface
from cfar.io import fingerprint,write_json
from cfar.synthetic_star import rectangle


def room_components(audit,storey):
    rooms={s["global_id"]:s for s in audit["spaces"] if s["eligible"]and s["storey_id"]==storey}
    graph={rid:set()for rid in rooms}
    for a,b in combinations(rooms,2):
        x,y=Polygon(rooms[a]["polygon"]),Polygon(rooms[b]["polygon"])
        if x.intersection(y).area<=1e-8 and x.boundary.intersection(y.boundary).length>1e-8:
            graph[a].add(b);graph[b].add(a)
    components=[];unseen=set(rooms)
    while unseen:
        seen={min(unseen)};stack=list(seen)
        while stack:
            for nxt in graph[stack.pop()]-seen:seen.add(nxt);stack.append(nxt)
        unseen-=seen
        if len(seen)>1:components.append([rooms[r]for r in sorted(seen)])
    return sorted(components,key=lambda c:(-len(c),tuple(s["global_id"]for s in c)))


def clear_slot(shapes,obstacles):
    common=shapes[0]
    for shape in shapes[1:]:common=common.intersection(shape)
    common=common.difference(unary_union(obstacles))
    if common.is_empty:raise ValueError("no aligned clear footprint")
    x0,y0,x1,y1=common.bounds
    for ix in range(ceil(x0/.8),floor((x1-.7)/.8)+1):
        for iy in range(ceil(y0/.8),floor((y1-.7)/.8)+1):
            square=box(.8*ix,.8*iy,.8*ix+.7,.8*iy+.7)
            if common.covers(square):return list(map(list,square.exterior.coords))
    raise ValueError("no common fixed-grid 0.7m slot")


def build_subset(audit,storeys,components):
    if any(len(c)!=2 for c in components):raise ValueError("current parallel-chain admission requires a largest component of exactly two rooms")
    # Keep every conservative obstacle. Exact duplicate bounds may be removed;
    # this leaves the obstacle union unchanged, with source counts recorded.
    bounds=sorted({tuple(b["bounds"])for b in audit["background"]})
    obstacles=[rectangle(*b)for b in bounds];obs=[box(*b)for b in bounds]
    pairs=[sorted(c,key=lambda s:(Polygon(s["polygon"]).centroid.x,s["global_id"]))for c in components]
    slots=[clear_slot([Polygon(pair[j]["polygon"])for pair in pairs],obs)for j in range(2)]
    all_shapes=[Polygon(s["polygon"])for pair in pairs for s in pair]+obs
    boundary=rectangle(*unary_union(all_shapes).envelope.buffer(1).bounds)
    pids=["experimental0","experimental1"];floors=[];connections=[];actions=[]
    for i,(storey,pair) in enumerate(zip(storeys,pairs)):
        floor=dict(floor_id=storey["global_id"],elevation_m=storey["elevation_m"],boundary=boundary,
            rooms=[dict(room_id=s["global_id"],label=s["name"],polygon=s["polygon"])for s in pair],
            adjacency_edges=[],access_edges=[],obstacles=obstacles,reserved_portal_zones=slots)
        floor["adjacency_edges"]=[list(e)for e in sorted(computed_adjacency(floor))]
        first,second=[Polygon(s["polygon"])for s in pair]
        wall=first.boundary.intersection(second.boundary)
        if wall.geom_type!="LineString"or wall.length<.7:raise ValueError("no single shared wall supporting experimental opening")
        x0,y0,x1,y1=wall.bounds;cx=(x0+x1)/2;cy=(y0+y1)/2
        if abs(x1-x0)<1e-8:
            opening=[[cx,cy-.35],[cx,cy+.35]]
            patches=[rectangle(cx-.7,cy-.35,cx,cy+.35),rectangle(cx,cy-.35,cx+.7,cy+.35)]
        else:raise ValueError("current paired-chain protocol uses vertical shared walls; no rotation or polygon changes allowed")
        cid=f"hypothetical-door-{i}"
        connections.append(dict(connection_id=cid,evidence_id=cid,u=pair[0]["global_id"],v=pair[1]["global_id"],kind="door",
            existing=True,physical_profiles=pids,geometry=dict(width_m=.7,opening=opening,
                landings=[dict(room_id=s["global_id"],polygon=patch)for s,patch in zip(pair,patches)])))
        floor["access_edges"]=[dict(edge_id=cid,connection_id=cid,permitted_profiles=pids)]
        floors.append(floor)
    for side in range(2):
        for i in range(len(pairs)-1):
            cid=f"hypothetical-{'L'if side==0 else'R'}{i}";aid=f"{'L'if side==0 else'R'}{i}"
            records=[dict(room_id=pairs[f][side]["global_id"],polygon=slots[side])for f in(i,i+1)]
            connections.append(dict(connection_id=cid,evidence_id=cid,u=records[0]["room_id"],v=records[1]["room_id"],kind="lift",
                existing=False,physical_profiles=pids,geometry=dict(asset_id=f"hypothetical-shaft-{side}",width_m=.7,
                    rise_m=storeys[i+1]["elevation_m"]-storeys[i]["elevation_m"],run_m=1,landings=records,footprints=records)))
            actions.append(dict(action_id=aid,type="physical_intervention",cost=1 if side==0 else 1.1,requires=[],excludes=[],
                evidence_ids=[cid],effects=[dict(op="activate_connection",connection_id=cid,permitted_profiles=pids)],
                geometry_certificate=dict(geometry_model="reserved_interfaces_2d_v1",connection_ids=[cid],changed_floor_ids=[])))
    obligations=[]
    for q,pid in enumerate(pids):
        for i in range(1,len(pairs)):
            # Profile zero needs both rooms; profile one needs every right room.
            for side in ((0,1)if q==0 else(1,)):
                obligations.append(dict(obligation_id=f"O{q}-{i}-{side}",source=pairs[0][0]["global_id"],
                    target=pairs[i][side]["global_id"],profile_id=pid))
    instance=dict(schema_version="0.1.0",building_id=audit["provenance"]["building"]+"-multiroom-controlled",
        description="Unchanged IFC room subset with nonempty adjacency; ALL doors/access permissions, profiles, reservations, lifts and prices hypothetical; not original portal restoration.",
        floors=floors,connections=connections,actions=actions,portals=[],original_restoration_actions=[],obligations=obligations,
        profiles=[dict(profile_id=pid,min_width_m=w,clearance_m=w,can_use_stairs=False,max_slope=.1)for pid,w in zip(pids,(.4,.5))])
    recognize_physical_interface(instance)
    restricted=deepcopy(instance)
    for floor in restricted["floors"][1:-1]:floor["access_edges"][0]["permitted_profiles"]=pids[:1]
    recognize_physical_interface(restricted)
    impossible=deepcopy(restricted);impossible["actions"]=[a for a in impossible["actions"]if a["action_id"].startswith("L")]
    return {"open-horizontal":instance,"restricted-horizontal":restricted,"no-right-candidates":impossible}


def select_subset(audit):
    if any("error"in b for b in audit["background"]):raise ValueError("unmapped background")
    storeys=audit["storeys"];components=[room_components(audit,s["global_id"])for s in storeys]
    rejections=[]
    # Largest consecutive-storey blocks first, then source elevation/IDs. No
    # intermediate source storey is skipped, even when it has no eligible rooms.
    for count in range(len(storeys),1,-1):
        for start in range(len(storeys)-count+1):
            choices=components[start:start+count]
            if any(not c for c in choices):continue
            for selected in product(*choices):
                try:return build_subset(audit,storeys[start:start+count],selected),rejections
                except ValueError as error:rejections.append(dict(storeys=[s["global_id"]for s in storeys[start:start+count]],reason=str(error)))
    raise ValueError("no consecutive multi-room subset admitted; "+str(len(rejections))+" attempted blocks rejected")


def build(audits,output):
    if output.exists()and any(output.iterdir()):raise ValueError("fresh output required")
    rows=[]
    from cfar.errors import ValidationError
    for path in sorted(audits.glob("*.json")):
        audit=json.loads(path.read_text())
        if "spaces"not in audit:continue
        name=audit["provenance"]["building"]
        row=dict(source_building_id=name,source_ifc_sha256=audit["provenance"]["sha256"],audit_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                 source_storeys=len(audit["storeys"]),source_spaces=len(audit["spaces"]),
                 connected_component_sizes={s["global_id"]:[len(c)for c in room_components(audit,s["global_id"])]for s in audit["storeys"]})
        try:
            variants,rejections=select_subset(audit)
            row.update(status="controlled-subset-admitted",distinct_subsets=1,variants=len(variants),rejections=rejections,
                selected_storeys=[f["floor_id"]for f in next(iter(variants.values()))["floors"]],
                assumptions="hypothetical existing doors, profile permissions, lift templates, reservations and prices; original room polygons and obstacle union retained")
            for kind,instance in variants.items():
                write_json(output/"instances"/(name+"-"+kind+".json"),instance)
            write_json(output/"sources"/(name+".json"),row)
        except (ValueError,ValidationError)as error:row.update(status="unsupported",reason=str(error),distinct_subsets=0,variants=0)
        rows.append(row);write_json(output/"screening.json",rows)
        print(name,row["status"],flush=True)
    return rows


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--audits",type=Path,required=True);parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args();build(args.audits,args.output)
