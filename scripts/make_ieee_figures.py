"""Vector research figures regenerated from saved benchmark inputs and manifests."""
import argparse
import hashlib
import json
from pathlib import Path
from statistics import median
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch, FancyBboxPatch, Polygon
import numpy as np
from cfar.io import write_json
from build_paper import read_case

BLUE='#174d78';ORANGE='#ba5a1c';GREEN='#23764b';RED='#a02c38';GRAY='#5b6570'
plt.rcParams.update({'font.family':'serif','font.serif':['Times New Roman','DejaVu Serif'], 'font.size':8,
    'axes.labelsize':8,'axes.titlesize':9,'legend.fontsize':8,'xtick.labelsize':8,'ytick.labelsize':8,
    'pdf.fonttype':42,'ps.fonttype':42,'axes.spines.top':False,'axes.spines.right':False})


def save(fig,path):
    fig.savefig(path.with_suffix('.pdf'),bbox_inches='tight',pad_inches=.06)
    fig.savefig(path.with_suffix('.png'),dpi=200,bbox_inches='tight',pad_inches=.06)
    plt.close(fig)


def edge(ax,a,b,color=BLUE,style='-',width=1.6):
    ax.plot([a[0],b[0]],[a[1],b[1]],color=color,ls=style,lw=width,zorder=1)


def box(ax,x,y,w,h,label,color=BLUE):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.015',fc='white',ec=color,lw=1))
    ax.text(x+w/2,y+h/2,label,ha='center',va='center',fontsize=8)


def pipeline(output):
    fig,ax=plt.subplots(figsize=(7.1,1.8));ax.set(xlim=(0,10),ylim=(0,2.2));ax.axis('off')
    labels=['Frozen rooms /\nprofiles / actions','Validation + cells\n+ complete units','Owned-cell state\n+ full paid effects','Profile witnesses\n+ weighted basis','Full-action replay\n+ status / manifests']
    for i,label in enumerate(labels):
        box(ax,i*2,.8,1.75,.8,label)
        if i<4:ax.add_patch(FancyArrowPatch((i*2+1.8,1.2),(i*2+1.98,1.2),arrowstyle='->',mutation_scale=10,color=GRAY))
    ax.text(5,.28,'Geometry and original action costs remain intact; only reachability witnesses are compressed.',ha='center',color=GRAY)
    save(fig,output/'pipeline')


def demo(demo_path,output):
    instance=json.loads((demo_path/'input.json').read_text());before=json.loads((demo_path/'before.json').read_text());after=json.loads((demo_path/'result.json').read_text())
    fig,axes=plt.subplots(1,2,figsize=(7.1,2.4))
    for stage,ax in enumerate(axes):
        ax.axis('off');ax.set(xlim=(-.2,3.2),ylim=(-.5,2.1))
        pos={'S':(.2,0),'C':(.2,1.4),'T0':(1.6,1.4),'T1':(2.9,1.4)}
        # Nodes/positions are schematic; route satisfaction is loaded from saved evidence.
        for name,xy in pos.items():
            ax.scatter(*xy,s=170,color='white',edgecolor=BLUE,zorder=3)
            ax.text(xy[0],xy[1],name,ha='center',va='center',fontsize=8)
        edge(ax,pos['C'],pos['T0'],GRAY)
        ax.text(.9,1.76,'Door: profile 0 only',ha='center',fontsize=8)
        edge(ax,pos['S'],pos['C'],GRAY)
        ax.text(.31,.75,'Baseline lift\nboth profiles',fontsize=8,color=GRAY)
        if stage:
            edge(ax,pos['S'],pos['T0'],GREEN);edge(ax,pos['S'],pos['T1'],GREEN)
            ax.text(1.6,.13,'One original bundle A\nTwo lifts, cost 3',ha='center',color=GREEN)
        ax.set_title(('Before: 1/4 obligations' if stage==0 else 'After: 4/4 obligations'),fontweight='bold')
        paths=before['paths'] if stage==0 else after['reachability']['paths']
        ax.text(1.5,-.42,'Profile 0: '+str(sum(paths[f'O0{i}'] is not None for i in (0,1)))+'/2; profile 1: '+str(sum(paths[f'O1{i}'] is not None for i in (0,1)))+'/2',ha='center')
    fig.tight_layout();save(fig,output/'motivating_demo')


def unit_witness(output):
    fig,axes=plt.subplots(1,2,figsize=(7.1,2.7));left,right=axes
    for ax in axes:ax.axis('off');ax.set(xlim=(0,4),ylim=(-.5,3.7))
    acts={'L0':(.35,3),'M0':(.35,2),'L1':(.35,1),'M1':(.35,0)}
    owners={'owner 0':(2.9,2.6),'bridge':(2.9,1.5),'owner 1':(2.9,.4)}
    for aid,xy in acts.items():box(left,xy[0],xy[1],.6,.4,aid)
    for oid,xy in owners.items():box(left,xy[0],xy[1],.8,.45,oid)
    for a,o in [('L0','owner 0'),('M0','owner 0'),('L1','owner 1'),('M1','owner 1'),('L0','bridge'),('L1','bridge')]:
        edge(left,(acts[a][0]+.6,acts[a][1]+.2),(owners[o][0],owners[o][1]+.22),GRAY,width=.9)
    left.set_title('(a) One complete coupling unit; genuine h=2')
    left.text(2,-.4,'Incidence joins the owners through the shared bridge.',ha='center',fontsize=8)
    pos=[(.4,2.6),(1.45,2.6),(2.5,2.6),(3.55,2.6)]
    for i,xy in enumerate(pos):
        right.scatter(*xy,s=120,facecolor='white',edgecolor=BLUE,zorder=3);right.text(xy[0],xy[1],f'R{i}',ha='center',va='center',fontsize=8)
    edge(right,pos[0],pos[1],BLUE);edge(right,pos[1],pos[2],GREEN);edge(right,pos[2],pos[3],BLUE,'--')
    right.text(1.45,3.18,'A000 supplies two disconnected edges',ha='center',fontsize=8)
    right.text(2.03,2.09,'Other paid action\nconnects the target',ha='center',color=GREEN,fontsize=8)
    for i,xy in enumerate(pos):
        right.add_patch(Rectangle((xy[0]-.21,.85),.42,.6,fc='#dce6ee' if i<2 else '#f0d7db',ec=BLUE if i<2 else RED,hatch='//' if i>=2 else None))
    right.text(2,.4,'All full footprints stay occupied, including R2/R3.',ha='center',fontsize=8)
    right.set_title('(b) Thin witness; complete paid geometry')
    right.text(2,-.4,'Dashed supplied edge may be absent from the witness.',ha='center',fontsize=8)
    fig.tight_layout();save(fig,output/'unit_witness')


def scaling(controlled,output):
    fig,axes=plt.subplots(1,2,figsize=(7.1,2.65));ax,owners=axes
    for method,color,label in [('recognition',GRAY,'Recognition'),('compressed',BLUE,'Compressed end-to-end'),('uncompressed',ORANGE,'Uncompressed end-to-end')]:
        xs=[];ys=[]
        for n in (8,32,64,128):
            v=read_case(controlled,f'dense-{n}')[method];times=[p['elapsed_seconds'] for p in v]
            xs.append(n);ys.append(median(times));ax.scatter([n]*len(times),times,color=color,s=12,alpha=.45)
        ax.plot(xs,ys,marker='o',ms=3,lw=1,color=color,label=label)
    ax.set(xscale='log',yscale='log',xlabel='Candidate actions',ylabel='Wall time (s)',title='(a) Private alternatives: h=1');ax.set_xticks([8,32,64,128],['8','32','64','128']);ax.grid(alpha=.2);ax.legend(loc='upper left')
    hs=[];raw=[];retained=[]
    for h in (2,3,4,8,16):
        result=read_case(controlled,f'owners-{h}')['compressed'][0]['result'];hs.append(result['parameters']['h']);raw.append(result['statistics']['peak_raw_states']);retained.append(result['statistics']['peak_retained_states'])
    owners.plot(hs,raw,'o-',color=BLUE,label='Peak raw');owners.plot(hs,retained,'x--',color=ORANGE,label='Peak retained')
    owners.set(xlabel='Owners per cell within one unit (h)',ylabel='Peak states',title='(b) Genuine owner competition');owners.grid(alpha=.2);owners.legend()
    fig.tight_layout();save(fig,output/'scaling')


def compression(controlled,output):
    fig,ax=plt.subplots(figsize=(3.5,2.4));cyclic=None
    for folder in sorted(controlled.iterdir()):
        if not folder.is_dir():continue
        vals=read_case(controlled,folder.name)
        if vals['compressed'][0]['status'] not in ('optimal','infeasible') or vals['uncompressed'][0]['status'] not in ('optimal','infeasible'):continue
        c=median(v['elapsed_seconds'] for v in vals['compressed']);u=median(v['elapsed_seconds'] for v in vals['uncompressed']);r=vals['compressed'][0]['result']['statistics']['peak_raw_states']
        ax.scatter(r,c/u,s=18,color=BLUE,alpha=.7)
        if folder.name=='cyclic':cyclic=(r,c/u)
    ax.axhline(1,color=GRAY,ls='--',lw=1)
    if cyclic:ax.annotate('Cyclic: 4 rows removed',xy=cyclic,xytext=(8,1.34),arrowprops=dict(arrowstyle='->',lw=.7),fontsize=8)
    ax.set(xscale='log',xlabel='Peak raw states (compressed)',ylabel='Median time ratio (compressed / full)',title='Descriptive overhead; three samples per mode')
    ax.grid(alpha=.2);fig.tight_layout();save(fig,output/'compression')


def statuses(controlled,output):
    names=sorted(p.name for p in controlled.iterdir() if p.is_dir());methods=['recognition','compressed','uncompressed','oracle']
    status_codes={'not-run':0,'recognized':1,'optimal':2,'infeasible':3,'limit-exceeded':4,'unsupported':5,'timeout':6,'error':7}
    data=[]
    for name in names:
        values=read_case(controlled,name);data.append([status_codes[values[m][0]['status']] if m in values else 0 for m in methods])
    colors=['#efefef','#9ac4d8','#70af8d','#d4b277','#cf7990','#9896c1','#b45538','#111111']
    from matplotlib.colors import ListedColormap,BoundaryNorm
    fig,ax=plt.subplots(figsize=(7.1,6.4));ax.imshow(data,cmap=ListedColormap(colors),norm=BoundaryNorm(np.arange(-.5,8.5),8),aspect='auto')
    ax.set_xticks(range(4),['Recognition','Compressed','Uncompressed','Small oracle']);ax.set_yticks(range(len(names)),[n.replace('shaft-','S-').replace('owners-','h=') for n in names]);ax.tick_params(axis='both',length=0)
    for i,row in enumerate(data):
        for j,code in enumerate(row):ax.text(j,i,['--','R','O','I','L','U','T','E'][code],ha='center',va='center',fontsize=8)
    ax.set_title('All 37 authored cases; first sample status (repetitions preserved in manifests)')
    ax.text(.5,-.11,'R: recognized   O: optimal   I: infeasible   L: limit exceeded\nU: unsupported   --: oracle omitted by protocol',transform=ax.transAxes,ha='center',fontsize=8)
    fig.tight_layout();save(fig,output/'status_matrix')


def building_plan(building,output):
    instance=json.loads((building/'duplex-A-bundle/input.json').read_text())
    fig,axes=plt.subplots(1,2,figsize=(3.5,3.7),sharex=True,sharey=True)
    for i,(floor,ax) in enumerate(zip(instance['floors'],axes)):
        room=floor['rooms'][0]
        ax.add_patch(Polygon(room['polygon'],fc='#e7f0f7',ec=BLUE,lw=1.1))
        for obstacle in floor['obstacles']:
            if max(p[0] for p in obstacle)<6:continue
            ax.add_patch(Polygon(obstacle,fc='#d9d9d9',ec=GRAY,hatch='///',lw=.8))
        for j,res in enumerate(floor['reserved_portal_zones']):
            ax.add_patch(Polygon(res,fc='#c6dfcf',ec=GREEN,lw=1.2))
            coordinates=np.asarray(res)
            if np.array_equal(coordinates[0],coordinates[-1]):coordinates=coordinates[:-1]
            center=coordinates.mean(axis=0)
            ax.text(*center,f'X{j}',ha='center',va='center',fontsize=8)
        ax.set(xlim=(6.0,8.65),ylim=(-17.9,-5.9),aspect='equal',xlabel='x (m)',title=room['label'])
        ax.set_xticks([6,7,8]);ax.grid(alpha=.15);ax.tick_params(labelsize=8)
    axes[0].set_ylabel('y (m)');fig.text(.5,.005,'Blue: projected IFC room; gray: existing stair envelope.\nGreen: hypothetical reservations, selected by bundle A.',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.055,1,1));save(fig,output/'duplex_plan')


def semantic_costs(controls,output):
    rows=json.loads((controls/'summary.json').read_text())
    fig,ax=plt.subplots(figsize=(3.5,2.3));xs=np.arange(len(rows));width=.35
    ax.bar(xs-width/2,[float(r['strict_cost']) for r in rows],width,color=BLUE,label='Strict optimum')
    bars=ax.bar(xs+width/2,[float(r['original_cost']) for r in rows],width,color='#babfc5',label='Control selection (original cost)')
    for bar,row in zip(bars,rows):
        if not row['full_model_valid']:bar.set_facecolor('#f0d7db');bar.set_edgecolor(RED);bar.set_hatch('//')
    ax.set_xticks(xs,['Graph-only\nshared owner','No owner\nreuse','Per-effect\nprice','Graph-only\npaid geometry'])
    from matplotlib.patches import Patch
    ax.set(ylabel='Abstract original-action cost',ylim=(0,11))
    ax.legend(handles=[Patch(facecolor=BLUE,label='Strict optimum'),Patch(facecolor='#babfc5',label='Control selection')],loc='lower center',bbox_to_anchor=(.5,1.01),ncol=2,frameon=False)
    ax.grid(axis='y',alpha=.2)
    fig.tight_layout();save(fig,output/'semantic_controls')


def greedy_quality(controlled,optimizers,output):
    from decimal import Decimal
    from review_evidence import optimization_audit, samples
    optimization_audit(controlled,optimizers)
    rows=[]
    for folder in sorted(optimizers.iterdir()):
        if not folder.is_dir() or folder.name == 'state-limit':continue
        _,c=samples(optimizers,folder.name,'cp-sat');_,g=samples(optimizers,folder.name,'greedy')
        if c[0]['status']=='optimal' and g[0]['status']=='feasible':
            optimum=Decimal(c[0]['result']['cost']);heuristic=Decimal(g[0]['result']['cost'])
            if heuristic>optimum:rows.append((folder.name,float(optimum),float(heuristic)))
    if len(rows)!=4:raise ValueError('greedy figure narrative requires updating')
    fig,ax=plt.subplots(figsize=(3.5,2.5));xs=np.arange(len(rows));w=.36
    ax.bar(xs-w/2,[r[1] for r in rows],w,color=BLUE,label='Exact optimum')
    ax.bar(xs+w/2,[r[2] for r in rows],w,color=ORANGE,label='Valid greedy repair')
    labels={'cyclic':'Cyclic','separate_profiles':'Separate\nprofiles','shaft-4-2-0':'Shaft 4/2\nseed 0','shared_asset':'Shared\nasset'}
    ax.set_xticks(xs,[labels[r[0]] for r in rows]);ax.set_ylabel('Original action cost');ax.set_ylim(0,12);ax.grid(axis='y',alpha=.2);ax.legend(frameon=False,fontsize=7)
    fig.tight_layout();save(fig,output/'greedy_quality')


def generate(controlled,building,demo_path,output,controls,optimizers=None):
    output.mkdir(parents=True,exist_ok=True)
    if any(output.iterdir()):raise ValueError('fresh output required')
    pipeline(output);demo(demo_path,output);unit_witness(output);scaling(controlled,output);compression(controlled,output);statuses(controlled,output);building_plan(building,output);semantic_costs(controls,output)
    from review2_diagnostic_figure import diagnostic_figure
    diagnostic_figure(output)
    if optimizers:greedy_quality(controlled,optimizers,output)
    source_files=[p for root in (controlled,building,demo_path,controls)+((optimizers,) if optimizers else ()) for p in root.rglob('*.json')]
    write_json(output/'figure-provenance.json',dict(generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),matplotlib=matplotlib.__version__,python=sys.version,
        schematic_source_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in(Path(__file__).with_name('review2_diagnostic_figure.py'),Path(__file__).parents[1]/'src/cfar/review_generators.py')},
        sources={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files},
        schematic_figures=['pipeline','motivating_demo','unit_witness','complete_diagnostic'],plots='raw samples and medians; no DP-only subtraction or significance claim',
        outputs={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in output.glob('*.pdf')}))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--controlled',type=Path,required=True);parser.add_argument('--building',type=Path,required=True);parser.add_argument('--demo',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--controls',type=Path,required=True)
    parser.add_argument('--optimizers',type=Path)
    args=parser.parse_args();generate(args.controlled,args.building,args.demo,args.output,args.controls,args.optimizers)
