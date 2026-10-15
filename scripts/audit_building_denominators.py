"""Count source models, actual selected room subsets and deduplicated variants."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

from shapely.geometry import Polygon
from cfar.io import fingerprint,write_json


def audit(groups,audits,output):
    subsets={};variants=defaultdict(set);refs=defaultdict(list);sources={}
    known=set()
    for path in audits.glob("*.json"):
        data=json.loads(path.read_text())
        if "spaces"in data:known.add(data["provenance"]["building"])
    for root in groups:
        files=list(root.glob("*/input.json"))or list(root.glob("*.json"))
        for p in sorted(files):
            instance=json.loads(p.read_text())
            if "floors"not in instance:continue
            source=p.stem.split('-')[0]if p.name!="input.json"else p.parent.name.split('-')[0]
            if instance["building_id"].startswith("authored-"):continue
            if source not in known:raise ValueError("unmapped source prefix: "+str(p))
            pairs=tuple(sorted((f["floor_id"],tuple(sorted(r["room_id"]for r in f["rooms"])))for f in instance["floors"]))
            key=(source,pairs)
            shapes={r["room_id"]:r["polygon"]for f in instance["floors"]for r in f["rooms"]}
            if key in subsets:
                if not all(Polygon(shapes[r]).equals(Polygon(subsets[key][r]))for r in shapes):raise ValueError("same source IDs have changed geometry")
            else:subsets[key]=shapes
            variants[key].add(fingerprint(instance));refs[key].append(str(p.resolve()))
            sources[str(p.resolve())]=hashlib.sha256(p.read_bytes()).hexdigest()
    source_audits=[]
    for p in sorted(audits.glob('*.json')):
        data=json.loads(p.read_text())
        if "spaces"in data:source_audits.append(data)
    records=[]
    for (source,pairs),shapes in subsets.items():
        audit=next(a for a in source_audits if a["provenance"]["building"]==source)
        records.append(dict(source_building_id=source,selected_storeys=[f for f,_ in pairs],room_ids=sorted(shapes),
            rooms=len(shapes),source_rooms=len(audit["spaces"]),variants=len(variants[source,pairs]),
            full_building=len(shapes)==len(audit["spaces"])and len(pairs)==len(audit["storeys"]),references=refs[source,pairs]))
    result=dict(distinct_audited_source_models=len(source_audits),distinct_used_source_models=len({r['source_building_id']for r in records}),
        distinct_selected_subsets=len(records),deduplicated_variant_definitions=sum(r["variants"]for r in records),
        full_building_experiments=sum(r["full_building"]for r in records),subsets=records,source_hashes=sources,
        policy="Subset identity uses original source model, storey IDs and room IDs; coordinate equality checked. Repeated measurements and copied inputs do not create new variants.")
    write_json(output,result);print(json.dumps({k:v for k,v in result.items()if k not in{'subsets','source_hashes'}}))


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--groups",nargs="+",type=Path,required=True);p.add_argument("--audits",type=Path,required=True);p.add_argument("--output",type=Path,required=True)
    a=p.parse_args();audit(a.groups,a.audits,a.output)
