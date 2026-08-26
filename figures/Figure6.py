#!/usr/bin/env python3
from pathlib import Path
import json, hashlib, os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch

OUT = Path(__file__).resolve().parent
# Reviewer-friendly default: expect artifacts/ beside figures/. Override with PHASE0_ROOT if needed.
ROOT = Path(os.environ.get('PHASE0_ROOT', str(OUT.parent)))
PDF_OUT = OUT / 'figure6.pdf'
PNG_OUT = OUT / 'figure6.png'

# Frozen provenance checks: the visual is generated only after the paper-bearing
# live rows, verification ledger, fixed-call isolation result, and source file
# match the audited hashes.
paths = {
    'RUN_ROWS': ROOT/'artifacts/E2E_ATTR_AUTH_v1/scientific_v1/RUN_ROWS.jsonl',
    'LEDGER': ROOT/'artifacts/verification/verification_out/CLAIM_LEDGER.json',
    'POC': ROOT/'artifacts/verification/verification_out/POC_BYPASS_RESULT.json',
    'SRC': ROOT/'artifacts/external/attriguard_zenodo_v1/usenix-artifacts/main/pipeline/AttriGuard.py',
}
expected = {
    'RUN_ROWS': '46a1201a27266d615b68c209b610d0bdc4fc030514a4eca663937c8c61c1054f',
    'LEDGER': '7c26dc1c6f56ba78981909196dac7e120e3dfc019d39d7867126d3e4bfea4d7c',
    'POC': '4b184dfa5c63549f6745d63a610d323cb21fb1da5a4a3746f4a6130aee3d111d',
    'SRC': '6d28e2208efbd521bf3f2e90c553e57b11c786e65564eababacb8cdf4f8050d8',
}
def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()
for key, path in paths.items():
    assert path.exists() and sha256(path) == expected[key], (key, path)

rows = [json.loads(x) for x in paths['RUN_ROWS'].read_text().splitlines() if x.strip()]
assert len(rows) == 420 and all(r['status'] == 'SUCCESS' for r in rows)
conf_off = [r for r in rows if r['context'] == 'CONFLICT' and r['defense'] == 'OFF']
conf_on = [r for r in rows if r['context'] == 'CONFLICT' and r['defense'] == 'ON']
assert (len(conf_off), len(conf_on)) == (70, 70)
assert (sum(int(r['Z']) for r in conf_off), sum(int(r['Z']) for r in conf_on)) == (17, 2)
assert (sum(int(r['PAEF']) for r in conf_off), sum(int(r['PAEF']) for r in conf_on)) == (38, 47)

ledger = json.loads(paths['LEDGER'].read_text())
by_claim = {c['id']: c for c in ledger['claims']}
for cid, value in {
    'MECH.privileged_total': 168,
    'MECH.unaudited': 18,
    'MECH.qualifying_ctx': 18,
    'MECH.dualuse.paef1': 15,
    'MECH.dualuse.z1': 2,
}.items():
    assert by_claim[cid]['status'] == 'PASS' and by_claim[cid]['recomputed'] == value
assert json.loads(paths['POC'].read_text()).get('all_passed') is True
src = paths['SRC'].read_text()
assert 'skip_next_audit' in src and 'skip_empty_tool_results_audit' in src

plt.rcParams.update({
    'pdf.fonttype': 42,
    'ps.fonttype': 42,
    'font.family': 'DejaVu Sans',
    'font.size': 7.2,
})

INK = '#171717'
MUTED = '#555555'
RULE = '#9a9a9a'
GRID = '#d9d9d9'
OFF = '#cfcfcf'
BLUE = '#3d73b9'
BLUE_DARK = '#235d9f'
LIGHT = '#f2f2f2'
MID = '#dedede'

fig = plt.figure(figsize=(7.25, 4.78), facecolor='white')
ax = fig.add_axes([0,0,1,1])
ax.set_xlim(0,1); ax.set_ylim(0,1); ax.axis('off')

def box(x,y,w,h,lw=.75):
    ax.add_patch(Rectangle((x,y),w,h,fill=False,edgecolor=RULE,lw=lw))

def arrow(x1,y1,x2,y2,color=INK,lw=1.0,ls='-'):
    ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle='-|>',mutation_scale=9,
                                 linewidth=lw,color=color,linestyle=ls,shrinkA=0,shrinkB=0))

def bar(x,y,w,h,pct,color):
    ax.add_patch(Rectangle((x,y),w,h,facecolor='white',edgecolor=GRID,lw=.55))
    ax.add_patch(Rectangle((x,y),w*pct/100,h,facecolor=color,edgecolor='none'))

# panel dividers: open layout, no enclosing boxes
ax.plot([.448,.448],[.505,.955],color=GRID,lw=.85)
ax.plot([.285,.715],[.432,.432],color=GRID,lw=.95)

# ----- A -----
ax.text(.022,.965,'(a) Defense suppresses the selected\nunauthorized outcome',ha='left',va='top',fontsize=8.6,fontweight='bold',color=INK,linespacing=1.06)
ax.text(.022,.907,'Confirmatory live result across 420 executions',ha='left',va='top',fontsize=6.15,color=MUTED)
ax.text(.022,.881,'420/420 executions | 14 tasks | 6 cells | 5 repeats',ha='left',va='top',fontsize=5.9,color=MUTED)

ax.add_patch(Rectangle((.207,.832),.014,.014,facecolor=OFF,edgecolor='none'))
ax.text(.228,.839,'Defense off',va='center',fontsize=6.9,color=INK)
ax.add_patch(Rectangle((.320,.832),.014,.014,facecolor=BLUE,edgecolor='none'))
ax.text(.341,.839,'Defense on',va='center',fontsize=6.9,color=INK)

ax.text(.032,.768,'Selected unauthorized\noutcome',ha='left',va='center',fontsize=7.0,fontweight='bold',color=INK,linespacing=1.0)
bar(.227,.776,.105,.020,24.3,OFF); ax.text(.333,.786,'17/70 (24.3%)',va='center',fontsize=6.6,fontweight='bold',color=INK)
bar(.227,.730,.105,.020,2.9,BLUE); ax.text(.333,.740,'2/70 (2.9%)',va='center',fontsize=6.6,fontweight='bold',color=BLUE_DARK)
ax.text(.032,.690,'Unauthorized outcome falls from 24.3% to 2.9%.',ha='left',va='center',fontsize=7.1,fontweight='bold',color=INK)
ax.text(.032,.666,'Difference: +21.4 pp',ha='left',va='center',fontsize=5.55,color=MUTED)
ax.text(.032,.646,'95% CI: +4.3 to +42.9 pp.',ha='left',va='center',fontsize=5.55,color=MUTED)

ax.plot([.025,.425],[.620,.620],color=GRID,lw=.8)
ax.text(.032,.566,'User-authorized\noutcome',ha='left',va='center',fontsize=7.0,fontweight='bold',color=INK,linespacing=1.0)
bar(.227,.574,.105,.020,54.3,OFF); ax.text(.333,.584,'38/70 (54.3%)',va='center',fontsize=6.6,fontweight='bold',color=INK)
bar(.227,.528,.105,.020,67.1,BLUE); ax.text(.333,.538,'47/70 (67.1%)',va='center',fontsize=6.6,fontweight='bold',color=BLUE_DARK)
ax.text(.032,.493,'Authorized outcome: +12.9 pp; 95% CI -11.4 to +38.6.',ha='left',va='center',fontsize=5.55,fontweight='bold',color=INK)
ax.text(.032,.473,'The confidence interval includes zero.',ha='left',va='center',fontsize=5.8,fontweight='bold',color=MUTED)
ax.text(.032,.452,'Primary test: -24.3 pp (95% CI -47.1 to -4.3), opposite the predicted direction.',ha='left',va='center',fontsize=5.1,color=MUTED)

# ----- B -----
ax.text(.465,.965,"(b) A block changes the path; what happens next\ndetermines the protected outcome",ha='left',va='top',fontsize=8.25,fontweight='bold',color=INK,linespacing=1.05)
ax.text(.465,.905,'Pre-specified continuation check.',ha='left',va='top',fontsize=6.3,color=MUTED)

# unauthorized proposal path
uy=.780
ax.text(.620,uy,'Selected unauthorized\nproposal',ha='right',va='center',fontsize=6.45,fontweight='bold',color=INK,linespacing=1.0)
arrow(.635,uy,.686,uy)
ax.plot([.700,.700],[uy-.060,uy+.060],color=INK,lw=1.5)
ax.text(.700,uy+.073,'blocked',ha='center',va='bottom',fontsize=6.7,color=MUTED)
arrow(.715,uy+.025,.830,uy+.025,color=BLUE,lw=1.3)
ax.text(.842,uy+.026,'Authorized outcome\nrecovers',ha='left',va='center',fontsize=7.15,fontweight='bold',color=INK,linespacing=1.0)
ax.text(.890,uy-.008,'12/13',ha='center',va='center',fontsize=8.1,fontweight='bold',color=BLUE_DARK)
arrow(.715,uy-.035,.830,uy-.035,color=MUTED,lw=.8,ls=(0,(3,2)))
ax.text(.842,uy-.047,'Other outcome  1/13',ha='left',va='center',fontsize=6.4,color=MUTED)

ax.plot([.468,.978],[.686,.686],color=GRID,lw=.8,ls=(0,(2,2)))

# authorized proposal path
ay=.590
ax.text(.620,ay,'User-authorized\nproposal',ha='right',va='center',fontsize=6.45,fontweight='bold',color=INK,linespacing=1.0)
arrow(.635,ay,.686,ay)
ax.plot([.700,.700],[ay-.060,ay+.060],color=INK,lw=1.5)
ax.text(.700,ay+.073,'blocked',ha='center',va='bottom',fontsize=6.7,color=MUTED)
arrow(.715,ay,.830,ay,color=MUTED,lw=1.3)
ax.text(.842,ay+.008,'Authorized outcome\nis lost',ha='left',va='center',fontsize=7.15,fontweight='bold',color=INK,linespacing=1.0)
ax.text(.890,ay-.028,'9/9',ha='center',va='center',fontsize=8.1,fontweight='bold',color=MUTED)
ax.text(.722,.493,'A block is a state transition, not the final outcome.',ha='center',va='center',fontsize=7.25,fontweight='bold',color=INK)

# ----- C -----
ax.text(.022,.416,'(c) A defense intervention can change whether the next privileged call is checked',ha='left',va='top',fontsize=8.5,fontweight='bold',color=INK)
ax.text(.022,.382,'Exploratory source+trace; tested AttriGuard implementation only.',ha='left',va='top',fontsize=6.35,color=MUTED)

# left flow area x .03-.60
bx=[.055,.240,.425]; bw=.145; by=.252; bh=.068
labels=[
    'Defense returns\nonly empty\ntool results',
    'Internal skip state\nis set',
    'Next tool-call batch\ncan skip the\nordinary audit',
]
flow_y = by + .006
centers = []
for i,(x,lbl) in enumerate(zip(bx,labels)):
    cx=x+bw/2
    centers.append(cx)
    ax.text(cx,by+bh/2+.010,lbl,ha='center',va='center',fontsize=5.95,fontweight='bold' if i==1 else 'normal',color=INK,linespacing=1.0)
    # short half-divider: visual anchor without a card/box
    ax.plot([cx-bw*.23,cx+bw*.23],[flow_y,flow_y],color=RULE,lw=.75)

# Connect the half-dividers below the labels. Keeping the arrows on the
# divider baseline prevents the flow line from crossing any text.
for c1,c2 in zip(centers[:-1], centers[1:]):
    ax.add_patch(FancyArrowPatch(
        (c1+bw*.23, flow_y), (c2-bw*.23, flow_y),
        arrowstyle='-|>', mutation_scale=7.0,
        linewidth=.85, color=INK, shrinkA=2.0, shrinkB=2.0,
    ))

# denominator cards below corresponding flow nodes
counts=[
    ('44/210 defended runs','entered this state'),
    ('22/210 defended runs','later used it'),
    ('18/168 privileged calls','ran without ordinary audit'),
]
for x,(top,bottom) in zip(bx,counts):
    ax.text(x+bw/2,.205,top,ha='center',va='center',fontsize=6.15,fontweight='bold',color=INK)
    ax.text(x+bw/2,.181,bottom,ha='center',va='center',fontsize=5.9,color=MUTED)

ax.text(.312,.137,'All 18/18 unaudited privileged calls came immediately after the qualifying empty-result batch.',ha='center',va='center',fontsize=6.15,fontweight='bold',color=INK)

# divider + right outcome area
ax.plot([.615,.615],[.135,.330],color=GRID,lw=.9)
ax.text(.803,.355,'Unaudited calls had mixed outcomes',ha='center',va='center',fontsize=7.05,fontweight='bold',color=INK)
rx=.655; ry=.280; rw=.300; rh=.052
parts=[15/18,2/18,1/18]; cols=[BLUE,MID,LIGHT]
left=rx
for p,c in zip(parts,cols):
    w=rw*p
    ax.add_patch(Rectangle((left,ry),w,rh,facecolor=c,edgecolor='white',lw=.35))
    left += w
ax.text(rx+rw*(15/18)/2,ry+rh/2,'15',ha='center',va='center',fontsize=8.0,fontweight='bold',color='white')
ax.text(rx+rw*(15/18)+(rw*(2/18))/2,ry+rh/2,'2',ha='center',va='center',fontsize=7.0,fontweight='bold',color=INK)
ax.text(rx+rw*(17/18)+(rw*(1/18))/2,ry+rh/2,'1',ha='center',va='center',fontsize=6.7,fontweight='bold',color=INK)

legend=[('15  authorized / authorization-equivalent',BLUE),('2  selected unauthorized',MID),('1  neither',LIGHT)]
for j,(txt,c) in enumerate(legend):
    yy=.235-j*.037
    ax.add_patch(Rectangle((.660,yy-.007),.012,.012,facecolor=c,edgecolor='none',lw=0))
    ax.text(.681,yy,txt,ha='left',va='center',fontsize=6.25,color=INK)

ax.text(.803,.115,"Holding the next privileged call fixed reproduces\nthe transition; a local patch restores the audit.",ha='center',va='center',fontsize=6.15,fontweight='bold',color=MUTED,linespacing=1.05)
ax.text(.035,.055,'Security implication: a defense intervention can change what happens next and whether a later privileged call is checked.',ha='left',va='center',fontsize=6.35,fontweight='bold',color=INK)

fig.savefig(PDF_OUT)
fig.savefig(PNG_OUT,dpi=260)
print(PDF_OUT)
print(PNG_OUT)
