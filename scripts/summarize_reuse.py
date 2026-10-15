"""Audit the separately pinned cell-local checkpoint and its analytic witnesses."""
import argparse
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path
from statistics import median

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from cfar.io import fingerprint,write_json
from summarize_review2 import audit,tex


def summarize(root,analytic,output):
    rows,protocol,fps=audit(root)
    if output.exists()and any(output.iterdir()):raise ValueError("fresh output required")
    output.mkdir(parents=True,exist_ok=True)
    witnesses=json.loads(analytic.read_text())
    for witness in witnesses:
        name=witness["instance_id"];instance=json.loads((root/name/"input.json").read_text())
        if fingerprint(instance)!=witness["input_sha256"]:raise ValueError("analytic input mismatch")
        floors=sorted(instance["floors"],key=lambda f:f["elevation_m"])
        ranks={r["room_id"]:i for i,f in enumerate(floors)for r in f["rooms"]}
        catalog={c["connection_id"]:c for c in instance["connections"]};mandatory=set()
        if instance["portals"]or any(f["access_edges"]for f in floors):raise ValueError("chain lower bound has no baseline")
        if not all(ranks[o["source"]]==0 and ranks[o["target"]]==len(floors)-1 for o in instance["obligations"]):raise ValueError("chain terminal mismatch")
        for cut in range(len(floors)-1):
            suppliers=set()
            for a in instance["actions"]:
                for e in a["effects"]:
                    c=catalog[e["connection_id"]];u,v=sorted((ranks[c["u"]],ranks[c["v"]]))
                    if u<=cut<v and "profile0"in e["permitted_profiles"]:suppliers.add(a["action_id"])
            if len(suppliers)!=1:raise ValueError("cut is not uniquely supplied")
            mandatory.update(suppliers)
        if sorted(mandatory)!=sorted(witness["selected"]):raise ValueError("cut witness not required")
        for row in rows:
            if row["instance_id"]==name and row["status"]=="optimal":
                if row["objective_cost"]!=witness["optimum_cost"]or row["selected_action_ids"]!=sorted(mandatory):raise ValueError("analytic optimum disagreement")
    counts={m:dict(Counter(r["status"]for r in rows if r["solver"]==m))for m in sorted({r["solver"]for r in rows})}
    summaries={}
    for name in sorted({r["instance_id"]for r in rows}):
        group=[r for r in rows if r["instance_id"]==name]
        summaries[name]={}
        for method in sorted({r["solver"]for r in group}):
            samples=[r for r in group if r["solver"]==method]
            times=[r["end_to_end_seconds"]for r in samples if r["end_to_end_seconds"]is not None]
            construction=[r["phase_timings"].get("event_construction_seconds",r["phase_timings"].get("formulation_seconds"))for r in samples if r["phase_timings"]]
            construction=[v for v in construction if v is not None]
            summaries[name][method]=dict(statuses=dict(Counter(r["status"]for r in samples)),
                median_seconds=median(times)if times else None,
                min_seconds=min(times)if times else None,max_seconds=max(times)if times else None,
                peak_raw_states=max((r["peak_raw_states"]for r in samples if r["peak_raw_states"]is not None),default=None),
                median_rss_bytes=median([r["peak_memory_bytes"]for r in samples if r["peak_memory_bytes"]is not None]),
                parameters=samples[0].get("solver_parameters"),cost=samples[0]["objective_cost"],selected=samples[0]["selected_action_ids"],
                phase_medians={field:median([r["phase_timings"][field]for r in samples if r["phase_timings"]and r["phase_timings"].get(field)is not None])
                    for field in("recognition_seconds","optimization_seconds","replay_seconds")if any(r["phase_timings"]and r["phase_timings"].get(field)is not None for r in samples)},
                construction_seconds=median(construction)if construction else None,
                independent_replay_seconds=median([r["independent_replay_seconds"]for r in samples if r["independent_replay_seconds"]is not None])if any(r["independent_replay_seconds"]is not None for r in samples)else None)
    report=dict(measurements=len(rows),instance_count=len(summaries),protocol=protocol,status_counts=counts,
        cases=summaries,analytic_witnesses_verified=len(witnesses),solver_source_fingerprints=fps)
    write_json(output/"summary.json",report)
    plot(summaries,output)
    write_json(output/"provenance.json",dict(source_hashes={str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest()for p in list(root.rglob("*.json"))+[analytic]},
        generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        outputs={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in output.iterdir()if p.is_file()}))
    print(json.dumps(dict(measurements=len(rows),cases=len(summaries),counts=counts)))


def plot(cases,out):
    plt.rcParams.update({"font.family":"serif","font.size":8,"pdf.fonttype":42})
    fig,axes=plt.subplots(2,2,figsize=(7.1,4.9))
    xs=[4,8,16,32];methods=["compressed","full","reuse","cp-sat"]
    colors=["#174d78","#ba5a1c","#8b4486","#23764b"]
    axes[0,0].plot(xs,xs,"o-",label="complete-unit span",color=colors[0]);axes[0,0].plot(xs,[2]*4,"s-",label="action span",color=colors[2])
    axes[0,0].set(ylabel="measured look-ahead span",xlabel="floors",title="(a) Same owner, local activations");axes[0,0].legend(fontsize=7)
    for method,color in zip(methods,colors):
        values=[cases[f"chain-{n}"][method]for n in xs]
        if method!="cp-sat":
            axes[0,1].plot(xs,[r["peak_raw_states"]for r in values],"o-",label=method,color=color)
        axes[1,0].plot(xs,[r["median_seconds"]for r in values],"o-",label=method,color=color)
        axes[1,1].plot(xs,[r["median_rss_bytes"]/2**20 for r in values],"o-",label=method,color=color)
        for x,r in zip(xs,values):
            if "internal_cap"in r["statuses"]:
                for ax,y in((axes[0,1],r["peak_raw_states"]),(axes[1,0],r["median_seconds"]),(axes[1,1],r["median_rss_bytes"]/2**20)):
                    ax.scatter(x,y,marker="x",s=60,color="black",zorder=5)
    axes[0,1].set(yscale="log",ylabel="peak raw states",xlabel="floors",title="(b) Crosses are incomplete cap runs")
    axes[1,0].set(yscale="log",ylabel="function seconds",xlabel="floors",title="(c) Five-sample medians; cap time is not a solve")
    axes[1,1].set(ylabel="peak process RSS (MiB)",xlabel="floors",title="(d) RSS includes imports")
    for ax in axes.flat:ax.grid(alpha=.2)
    axes[1,0].legend(fontsize=7);fig.tight_layout();fig.savefig(out/"reuse_locality.pdf",bbox_inches="tight");plt.close(fig)


def paper_section(output):
    prov=json.loads((output/"provenance.json").read_text())
    for name,digest in prov["outputs"].items():
        if hashlib.sha256((output/name).read_bytes()).hexdigest()!=digest:raise ValueError("reuse summary output changed")
    d=json.loads((output/"summary.json").read_text())
    lines=[r"\section{Cell-Local Owner Expiration: Removing Avoidable Shaft Coupling}\label{sec:reuse}",
        "Complete global units can be unnecessarily broad: a sequence of independent adjacent-floor activations of one proposed shaft forms a unit spanning the whole building. We provide an alternative exact sweep that retains each owner name only until its last possible use at the same collision cell. Whole-action support and prices remain intact. This is a structural transfer using established resource-lifetime and representative-partition ideas.",
        r"\subsection{Constructed Schedule and Refined Parameters}",
        r"Let $L_a$ be the maximum span of one complete available action or active baseline edge. Sort actions by earliest touched floor, then original ID. For each owner--cell pair $(o,c)$, construct its first/last use indices $\ell(o,c),u(o,c)$ in this fixed order. Define $\kappa=\max_{e,c}|\{o:\ell(o,c)\le e\le u(o,c)\}|$. Both $L_a$ and $\kappa$ are computed, rather than assumed properties of all buildings. Their construction cost is included in recognition. The original complete-unit span $L_{unit}$ is recorded separately.",
        r"After processing action $e$, replace an occupied owner name by external occupancy only if $u(o,c)\le e$. Do not free the cell. Until that point retain its actual owner, permitting legitimate reuse. Each action is still purchased once, reserving every footprint before any graph-witness omission. An alternative event order requires recomputing these intervals; the current implementation rejects a stale reverse schedule.",
        r"\begin{lemma}[Cell-local expiration]\label{lem:local-expiry}After the last available action using $(o,c)$, replacing owner $o$ by external occupancy on $c$ preserves every future feasible selection.\end{lemma}",
        r"\begin{proof}A future action either avoids $c$ or uses a different owner there. Both recorded owner $o$ and external occupancy accept the first case and reject the second. Before the last use, such replacement could wrongly reject a same-owner continuation and is forbidden. Occupancy, paid effects and costs are never removed.\end{proof}",
        r"\begin{theorem}[Action-span owned-cell sweep]\label{thm:local-reuse}On the same recognized physical class, the unlimited-state cell-local sweep returns the exact original-action label in $T_{rec}+2^{O(prL_a+zL_a\log(\kappa+2))}\poly(B)$ time.\end{theorem}",
        r"\begin{proof}Process each whole action at its first support floor. All its effects and footprints lie in the next $L_a$ floors; no future event beginning later can touch an expired floor. This proves the window/forgetting condition without global unit completion. At an event, a retained owner name belongs to an interval covering that event, giving at most $\kappa$ owner possibilities per live cell, plus empty/external. Thus the resource factor is at most $(\kappa+2)^{zL_a}$. The thin-witness, stable-label and product-basis arguments of Appendix~\ref{app:proof} apply unchanged to the $prL_a$ live positions. Lemma~\ref{lem:local-expiry} preserves future compatibility when names expire. Every optimum materialization has a corresponding root-component witness branch, and every accepting branch replays to the full strict repair. Polynomial event/interval construction and label bit work give the stated bound.\end{proof}",
        "This is a different sufficient structural regime, not a claim that it always dominates the complete-unit sweep. A continuous shaft with local independent activations has unbounded global unit span but action span two and owner-interval overlap one. Private single-use alternatives also have overlap one, because their names expire immediately. Genuinely overlapping reusable-owner intervals can make the new parameter large. A disconnected atomic three-floor action still has action span at least three.",
        r"The same lifetime schedule also narrows the generic resource-incidence decomposition: keep live profile vertices/cells and one Usage object per live owner--cell pair, yielding $O(prL_a+zL_a+p+zL_a\kappa)$ live labels. The fixed weighted logic formulation therefore already supplies a generic algorithm through this narrower expression. Our displayed logarithmic owner term compares resource-domain accounting with that particular expression; it does not prove priority or superiority over all domain-valued resource DPs.",
        r"\subsection{Separate Pinned Comparison}",
        str(d["measurements"])+" additional fresh-process measurements cover "+str(d["instance_count"])+" declared inputs with five repetitions per optimizer. This is a separate code revision, not pooled timing data with the earlier suite. It reuses the same three Molio controls, not new source buildings or subsets. All completed exact labels agree. Independent selected-set replay and four mechanically verified unique-cut lower bounds support the chain optima; larger chains are analytically certified rather than exhaustively enumerated.",
        r"\begin{table}[t]\caption{Authored Shared-Shaft Chains; Same Physical Inputs and Budgets}\label{tab:reuse-chain}\centering\scriptsize\begin{tabular}{rrrrrr}\toprule Floors & $L_{unit}$ & $L_a$ & $\kappa$ & Unit raw & Local raw\\\midrule"]
    for n in(4,8,16,32):
        c=d["cases"][f"chain-{n}"];p=c["reuse"]["parameters"]
        old=str(c["compressed"]["peak_raw_states"])+(r"$^{*}$"if"internal_cap"in c["compressed"]["statuses"]else"")
        lines.append(f"{n} & {p['L_unit']} & {p['L']} & {p['kappa']} & {old} & {c['reuse']['peak_raw_states']}"+r"\\")
    lines += [r"\bottomrule\end{tabular}\\\scriptsize $^{*}$Internal cap, not a completed optimum.\end{table}",
        r"\begin{figure*}[t]\centering\includegraphics[width=.96\textwidth]{figures/reuse_locality.pdf}\caption{All declared chain sizes. The earlier complete-unit DP modes hit their 10,000-state cap on 16/32 floors; local expiration and CP-SAT complete. Crosses denote incomplete searches, including their observed time/RSS. Process RSS includes imports. Small timing differences do not imply general superiority.}\label{fig:reuse-locality}\end{figure*}"]
    c=d["cases"]["molio-restricted-horizontal"]
    lines.append(r"\begin{table*}[t]\caption{Restricted-Horizontal Molio Timing Breakdown (Five-Run Medians, Seconds)}\label{tab:reuse-phases}\centering\scriptsize\begin{tabular}{lrrrrrrr}\toprule Method & Recognition & Construction & Optimization & Internal replay & Extra replay & End-to-end & RSS MiB\\\midrule")
    for method in("compressed","full","reuse","cp-sat"):
        sample=c[method];phases=sample["phase_medians"]
        values=[phases.get("recognition_seconds"),sample["construction_seconds"],phases.get("optimization_seconds"),phases.get("replay_seconds"),sample["independent_replay_seconds"],sample["median_seconds"],sample["median_rss_bytes"]/2**20]
        lines.append(tex(method)+" & "+" & ".join("--"if v is None else f"{v:.4f}"for v in values)+r"\\")
    lines.append(r"\bottomrule\end{tabular}\end{table*}")
    lines.append("Construction denotes DP event construction or CP-SAT formulation; recognition includes validation, geometry, cells and unit/component construction. Extra selected-set replay is separate from function end-to-end time. Hashing/result packaging and nonadditive medians explain residual differences; phases are not a subtraction-based DP-only timing estimate. Each worker preimports the same comparator modules, so process RSS includes a common library baseline and is not a minimal-deployment memory estimate.")
    lines.append("For the restricted-horizontal eight-room Molio input, all methods retain optimum cost 3.3. Peak raw states decrease from "+str(c["compressed"]["peak_raw_states"])+" in the complete-unit sweep to "+str(c["reuse"]["peak_raw_states"])+" with cell-local expiration; the window decreases from four floors to two. Five-run median end-to-end times are "+f"{c['compressed']['median_seconds']:.3f}"+" seconds (compressed unit), "+f"{c['reuse']['median_seconds']:.3f}"+" (local expiration), and "+f"{c['cp-sat']['median_seconds']:.3f}"+" (CP-SAT). Geometry recognition remains included. These descriptive local measurements show the state distinction and do not establish a universal speed ranking. The single-profile chains have elementary analytical optima; they diagnose interface accounting rather than establish hard-instance novelty.")
    lines += [r"\subsection{Practical Selection Rule and Remaining Boundary}",
        "Prefer testing the local-expiration DP when complete units span many floors but individual actions and cell-local reusable-owner overlap remain small. The complete-unit method can remain appropriate when grouping a compact unit avoids many simultaneous owner intervals. CP-SAT is a strong default comparator on the common recognized/cost-range class and solves every declared chain here. Uncompressed mode avoids cut-matrix limits when its full state set remains manageable. Neither optimizer validates unsupported geometry, missing original access evidence or statutory compliance. A generic domain-valued resource formulation may reproduce this bound; independent proof review and algorithmic priority remain open."]
    return "\n\n".join(lines)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--evidence",type=Path,required=True);parser.add_argument("--analytic",type=Path,required=True);parser.add_argument("--output",type=Path,required=True)
    a=parser.parse_args();summarize(a.evidence,a.analytic,a.output)
