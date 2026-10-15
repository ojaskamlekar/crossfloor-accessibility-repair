"""Complete authored explanatory example; measured results are checked separately."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle


def diagnostic_figure(output):
    from make_ieee_figures import save,BLUE,GREEN,RED,GRAY
    fig,axes=plt.subplots(2,2,figsize=(7.1,5.3))
    pos={f"{s}{f}":(x,1.5*f)for f in range(3)for s,x in(("L",0),("R",2))}
    def node(ax,name):
        x,y=pos[name];ax.scatter(x,y,s=150,fc="white",ec=BLUE,zorder=4)
        ax.text(x,y,name,ha="center",va="center",fontsize=7,zorder=5)
    def edge(ax,u,v,color,style="-",label=None,offset=0):
        a,b=pos[u],pos[v];ax.plot([a[0],b[0]],[a[1],b[1]],color=color,ls=style,lw=1.5)
        if label:ax.text((a[0]+b[0])/2+offset,(a[1]+b[1])/2,label,color=color,fontsize=7,ha="center",bbox=dict(fc="white",ec="none",pad=.3))
    for ax in axes.flat:ax.axis("off")
    for ax in axes.flat[:3]:
        ax.set(xlim=(-.6,2.6),ylim=(-.6,3.7))
        for f in range(3):
            edge(ax,f"L{f}",f"R{f}",GRAY,":"if f==1 else"-", "door: p0"if f==1 else"door: p0,p1")
        for name in pos:node(ax,name)
    ax=axes[0,0]
    edge(ax,"L0","L1",BLUE,label="A: a",offset=-.3)
    edge(ax,"R1","R2",BLUE,label="A: u",offset=.3)
    edge(ax,"L1","L2",GREEN,label="B: b",offset=-.3)
    edge(ax,"R0","R1",RED,label="C: v",offset=.3)
    ax.set_title("(a) Supplied actions and access",fontsize=9)
    ax.text(1,-.48,"A={a,u}: 1; B={b}: 1; C={v}: 0.5; D={w}: 3\nA is disconnected. D is a separate R0-R1 escape lift.",ha="center",va="top",fontsize=7)
    ax=axes[0,1];purchase=(1,1.0)
    ax.scatter(*purchase,s=120,marker="s",color=RED,zorder=3);ax.text(1.55,.65,"purchase A",ha="center",color=RED,fontsize=7)
    for name in("L0","L1","R1","R2"):
        x,y=pos[name];ax.plot([x,purchase[0]],[y,purchase[1]],"--",color=RED,lw=1)
    ax.set_title("(b) Incorrect purchase-vertex simplification",fontsize=9)
    ax.text(1,-.48,"Cost 1 falsely appears sufficient for p1.\nIt invents an L0-purchase(A)-R2 route.",ha="center",va="top",fontsize=7)
    ax=axes[1,0]
    edge(ax,"L0","L1",GREEN,label="A: a",offset=-.3);edge(ax,"L1","L2",GREEN,label="B: b",offset=-.3)
    edge(ax,"R1","R2",BLUE,"--",label="paid u",offset=.3)
    ax.set_title("(c) Correct optimum: A+B, cost 2",fontsize=9)
    ax.text(1,-.48,"p1 witness: L0-L1-L2-R2.\nA's u need not be in that witness; its footprint stays paid.",ha="center",va="top",fontsize=7)
    ax=axes[1,1];ax.set(xlim=(-.1,4.7),ylim=(-.8,4.2))
    for f in range(3):
        y=.7*f+.8
        ax.add_patch(Rectangle((.15,y),1.9,.58,fc="white",ec=GRAY));ax.add_patch(Rectangle((2.05,y),1.9,.58,fc="white",ec=GRAY))
        ax.text(.03,y+.25,f"F{f}",ha="right",fontsize=7)
        if f<2:ax.add_patch(Rectangle((.5,y+.1),.5,.35,fc="#c7dceb",ec=BLUE))
        if f>0:ax.add_patch(Rectangle((2.7,y+.1),.5,.35,fc="#ead1d5",ec=RED,hatch="//"))
    ax.set_title("(d) State after A, before B",fontsize=9)
    ax.text(2,3.8,"Left cells on F0/F1: owner left\nRight cells on F1/F2: owner right\nB reuses left; C conflicts on F1.",ha="center",va="top",fontsize=7)
    ax.text(2,.4,"p1 partition: {anchor,L0,L1} | {R2}\nlabel=(1,1,(A)); paid u omitted from witness only",ha="center",va="top",fontsize=7)
    ax.text(.5,-.03,"Schematic footprints; full instance has fixed room polygons.\nRoots: L0; targets: L1,R2, separately for p0 and p1.",transform=ax.transAxes,ha="center",va="top",fontsize=6.5)
    fig.tight_layout(h_pad=3,w_pad=2);save(fig,output/"complete_diagnostic")
