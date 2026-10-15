"""Generate IEEE master source/tables and audit all evidence/figure fingerprints."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
from statistics import median
from cfar.io import fingerprint,write_json
from build_paper import read_case
from review_evidence import optimization_table, public_section


def order_references(text):
    """IEEE numeric references follow first appearance, including generated text."""
    start=text.index(r'\begin{thebibliography}')
    stop=text.index(r'\end{thebibliography}',start)
    body=text[:start]
    block=text[start:stop]
    matches=list(re.finditer(r'\\bibitem\{([^}]+)\}',block))
    entries={m.group(1):block[m.start():matches[i+1].start() if i+1<len(matches) else len(block)]
             for i,m in enumerate(matches)}
    order=[]
    for citation in re.finditer(r'\\cite\{([^}]+)\}',body):
        for key in citation.group(1).split(','):
            key=key.strip()
            if key not in entries:raise ValueError('undefined citation: '+key)
            if key not in order:order.append(key)
    if set(order)!=set(entries):raise ValueError('uncited bibliography entries')
    return body+block[:matches[0].start()]+''.join(entries[k] for k in order)+text[stop:]


def table(caption,label,headers,rows,wide=False):
    env='table*' if wide else 'table'
    lines=[f'\\begin{{{env}}}[t]',f'\\caption{{{caption}}}\\label{{{label}}}',r'\centering\footnotesize\setlength{\tabcolsep}{3pt}',
        r'\begin{tabular}{'+'l'+'r'*(len(headers)-1)+'}',r'\toprule',' & '.join(headers)+r' \\',r'\midrule']
    lines += [' & '.join(str(v) for v in row)+r' \\' for row in rows]
    lines += [r'\bottomrule\end{tabular}',f'\\end{{{env}}}']
    return '\n'.join(lines)


def build(controlled,building,demo,controls,figures,output,optimizers,public_audit,public_results,review2=None):
    output.mkdir(parents=True,exist_ok=True)
    if any(output.iterdir()):raise ValueError('fresh empty output required')
    for root in (controlled,building):
        for f in root.iterdir():
            if f.is_dir():read_case(root,f.name)
    cases=['dense-8','dense-32','dense-64','dense-128','owners-2','owners-4','owners-8','owners-16','cyclic','rooms']
    pr=[];sr=[]
    for name in cases:
        v=read_case(controlled,name);r=v['compressed'][0]['result'];p=r['parameters'];s=r['statistics'];alias=name.replace('dense-','n=').replace('owners-','h=')
        pr.append([alias]+[p[k] for k in ('p','r','z','L','g','h')])
        sr.append([alias]+[f"{median(a['elapsed_seconds'] for a in v[m]):.4f}" for m in ('recognition','compressed','uncompressed')]+[s['peak_raw_states'],s['peak_retained_states'],r['cost'],','.join(r['selected'])])
    parameter_table=table('Selected Measured Interfaces','tab:measured',['Case','$p$','$r$','$z$','$L$','$g$','$h$'],pr)
    scaling_table=table('Selected Controlled Results (Three-Sample Median Seconds; Both DP Times Include Recognition and Replay)','tab:scaling',['Case','Recognition','Compressed','Uncompressed','Raw','Retained','Cost','Original IDs'],sr,True)
    br=[]
    for folder in sorted(building.iterdir()):
        if not folder.is_dir():continue
        v=read_case(building,folder.name);r=v['compressed'][0]['result']
        br.append([folder.name.replace('duplex-',''),'O' if r['status']=='optimal' else 'I',r['cost'] or '--',','.join(r['selected'] or []) or '--']+[f"{median(a['elapsed_seconds'] for a in v[m]):.4f}" for m in ('compressed','uncompressed')])
    building_table=table('Eight Variants of One Source Building (O: Optimal; I: Infeasible; Times in Seconds)','tab:building',['Variant','Status','Cost','IDs','Comp.','Full'],br)
    control_rows=json.loads((controls/'summary.json').read_text());cr=[]
    aliases=['Graph-only / shared asset','No same-owner reuse','Per-effect action price','Graph-only / paid unused effects']
    for alias,row in zip(aliases,control_rows):
        folder=controls/(row['case']+'-'+row['mode']);m=json.loads((folder/'manifest.json').read_text());instance=json.loads((folder/'input.json').read_text())
        if m['git_dirty'] or m['input_fingerprint']!=fingerprint(instance):raise ValueError('invalid control manifest')
        cr.append([alias,row['strict_cost'],row['original_cost'],','.join(row['selected']),'pass' if row['full_model_valid'] else 'collision'])
    control_table=table('Deliberate Semantic Controls (Not Valid Competing Repair Formulations)','tab:controls',['Altered semantics','Strict optimum','Control original cost','Control original IDs','Full replay'],cr,True)
    optimizer_table, optimizer_audit = optimization_table(controlled, optimizers)
    public_text, public_summary = public_section(public_audit, public_results)
    root=Path(__file__).resolve().parents[1]
    template=root/'paper/ieee/master.template.tex'
    original=(root/'paper/manuscript.template.tex').read_text()
    proof=original[original.index(r'\begin{lemma}[Ownership locality]'):original.index(r'\section{Experimental protocol}')]
    proof=re.sub(r'\\begin\{theorem\}.*?\\end\{theorem\}',r'\\subsection{Completeness, Soundness and Bit Complexity}',proof,flags=re.S)
    generic=(root/'paper/ieee/generic_appendix.tex').read_text()
    text=template.read_text().replace('@@PROCEDURE_APPENDIX@@',(root/'paper/ieee/procedure_appendix.tex').read_text()).replace('@@PROOF_APPENDIX@@',proof).replace('@@GENERIC_APPENDIX@@',generic).replace('@@PARAMETER_TABLE@@',parameter_table).replace('@@SCALING_TABLE@@',scaling_table).replace('@@CONTROL_TABLE@@',control_table).replace('@@BUILDING_TABLE@@',building_table).replace('@@OPTIMIZATION_TABLE@@',optimizer_table).replace('@@PUBLIC_BUILDING_SECTION@@',public_text)
    if review2:
        from summarize_review2 import paper_section
        text=text.replace('@@REVIEW2_SECTION@@',paper_section(review2))
    else:
        text=text.replace('@@REVIEW2_SECTION@@','')
    experimental_revision = json.loads((controlled/'protocol.json').read_text())['git_revision']
    optimizer_revision = json.loads((optimizers/'protocol.json').read_text())['git_revision']
    text=text.replace('@@EXPERIMENTAL_REVISION@@',experimental_revision[:7]).replace('@@OPTIMIZER_REVISION@@',optimizer_revision[:7])
    if '@@' in text:raise ValueError('unresolved template slot')
    text=order_references(text)
    abstract=re.search(r'\\begin\{abstract\}(.*?)\\end\{abstract\}',text,re.S).group(1)
    if len(abstract.split())>250 or '$' in abstract or r'\cite' in abstract:raise ValueError('IEEE abstract contract')
    (output/'master.tex').write_text(text,encoding='utf-8')
    shutil.copy2(root/'paper/ieee/IEEEtran.cls',output/'IEEEtran.cls')
    shutil.copytree(figures,output/'figures')
    if review2:
        for file in review2.glob('*.pdf'):shutil.copy2(file,output/'figures'/file.name)
    figure_manifest=json.loads((figures/'figure-provenance.json').read_text())
    for name,digest in figure_manifest['outputs'].items():
        if hashlib.sha256((figures/name).read_bytes()).hexdigest()!=digest:raise ValueError('figure hash mismatch')
    sources=[p for path in (controlled,building,demo,controls,optimizers,public_audit,public_results) for p in path.rglob('*.json')]
    if review2:sources += list(review2.glob('*'))
    sources += [root/'paper/ieee/procedure_appendix.tex',template,root/'paper/ieee/generic_appendix.tex',root/'paper/manuscript.template.tex',root/'paper/ieee/IEEEtran.cls',Path(__file__),root/'scripts/review_evidence.py']
    write_json(output/'master-provenance.json',dict(abstract_words=len(abstract.split()),figure_count=len(list((output/'figures').glob('*.pdf'))),
        source_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        experimental_revision=experimental_revision,optimizer_revision=optimizer_revision,
        optimizer_audit=optimizer_audit,public_summary=public_summary,
        semantic_control_revision=json.loads((controls/'shared_asset-graph-only/manifest.json').read_text())['git_revision'],
        formatting='unaltered IEEEtran conference class; no venue-specific page cap; author metadata intentionally absent'))
    print(output/'master.tex')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for name in ('controlled','building','demo','controls','figures','output','optimizers','public-audit','public-results'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--review2',type=Path)
    args=parser.parse_args();build(args.controlled,args.building,args.demo,args.controls,args.figures,args.output,args.optimizers,args.public_audit,args.public_results,args.review2)
