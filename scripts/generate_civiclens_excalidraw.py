#!/usr/bin/env python3
"""Generate Excalidraw JSON for CivicLens experimental setup diagram."""
import json

_n = [0]
def uid():
    _n[0] += 1
    return f"e{_n[0]}"

def cam(w, h, x, y):
    return {"type": "cameraUpdate", "width": w, "height": h, "x": x, "y": y}

def box(x, y, w, h, bg="transparent", sc="#1e1e1e", sw=1, rnd=False, op=100, label=None, dash=False):
    e = {"type": "rectangle", "id": uid(), "x": x, "y": y, "width": w, "height": h,
         "roughness": 0, "strokeColor": sc, "strokeWidth": sw,
         "backgroundColor": bg, "fillStyle": "solid", "opacity": op}
    if rnd: e["roundness"] = {"type": 3}
    if label: e["label"] = label
    if dash: e["strokeStyle"] = "dashed"
    return e

def txt(x, y, s, sz=20, c="#1e1e1e"):
    return {"type": "text", "id": uid(), "x": x, "y": y, "text": s,
            "fontSize": sz, "strokeColor": c, "roughness": 0,
            "width": len(s) * sz * 0.55, "height": sz * 1.25}

def ell(x, y, w, h, bg="transparent", sc="#1e1e1e", sw=1, label=None):
    e = {"type": "ellipse", "id": uid(), "x": x, "y": y, "width": w, "height": h,
         "roughness": 0, "strokeColor": sc, "strokeWidth": sw,
         "backgroundColor": bg, "fillStyle": "solid"}
    if label: e["label"] = label
    return e

def arr(x, y, dx, dy, sc="#1e1e1e", sw=2, end="arrow", start=None, dash=False):
    e = {"type": "arrow", "id": uid(), "x": x, "y": y, "width": dx, "height": dy,
         "points": [[0,0],[dx,dy]], "roughness": 0,
         "strokeColor": sc, "strokeWidth": sw, "endArrowhead": end}
    if start: e["startArrowhead"] = start
    if dash: e["strokeStyle"] = "dashed"
    return e

# ─── Colors ──────────────────────────────────────────────────────
NAV = "#1e1e1e"; RED = "#ef4444"; GRN = "#22c55e"; META = "#94a3b8"
CARD = "#ffffff"; BRD = "#e5e7eb"; VBRD = "#f59e0b"; VBG = "#fff3bf"
VDARK = "#92400e"; VMID = "#b45309"; ABG = "#d3f9d8"; ABRDR = "#86efac"
ADARK = "#166534"; BLUE = "#3b82f6"

# Personality short labels for headers
PSHORT = {
    'baseline':'base', 'introspective':'intro', 'nihilist':'nihil',
    'leader':'leader', 'follower':'follow', 'contrarian':'contr',
    'curious':'curio', 'devotee':'devot',
}
P = {
    'baseline':('#6B7280','#E5E7EB'), 'introspective':('#3B82F6','#DBEAFE'),
    'nihilist':('#374151','#F3F4F6'), 'leader':('#10B981','#D1FAE5'),
    'follower':('#06B6D4','#CFFAFE'), 'contrarian':('#EF4444','#FEE2E2'),
    'curious':('#F59E0B','#FEF3C7'), 'devotee':('#8B5CF6','#EDE9FE'),
}
AGENTS = [
    ('\u03b1','alpha','baseline'), ('\u03b2','beta','introspective'),
    ('\u03b3','gamma','nihilist'), ('\u03b4','delta','leader'),
    ('\u03b5','epsilon','follower'), ('\u03b6','zeta','contrarian'),
    ('\u03b7','eta','curious'), ('\u03b8','theta','baseline'),
]

els = []

# ═══ TITLE ═══════════════════════════════════════════════════════
els.append(cam(600, 450, 200, -20))
els.append(txt(30, 5, "CivicLens", 28))
els.append(txt(200, 10, "\u2014 Experimental Setup", 22, "#718096"))
els.append(arr(30, 42, 1080, 0, BRD, 1, None))

# ═══ CENTER — Moltbook UI ═══════════════════════════════════════
els.append(cam(600, 450, 240, 20))

MX, MY, MW = 310, 52, 440
MH = 550  # shorter — no wasted space
els.append(box(MX, MY, MW, MH, "#f8fafc", BRD, 2, True))

# Nav bar
els.append(box(MX, MY, MW, 38, NAV, NAV, 0, True))
els.append(box(MX, MY+26, MW, 12, NAV, NAV, 0))
els.append(txt(MX+12, MY+8, "moltbook", 22, RED))
els.append(box(MX+170, MY+7, 140, 24, "#374151", "#555", 1, True))
els.append(txt(MX+182, MY+11, "Search", 16, "#6b7280"))
els.append(txt(MX+MW-105, MY+10, "Submolts", 16, "#d4d4d4"))

# Sort tabs
ty = MY + 46
els.append(txt(MX+15, ty, "Hot", 16, RED))
els.append(box(MX+13, ty+20, 26, 3, RED, RED, 0, True))
for i, t in enumerate(["New", "Top", "Discussed"]):
    els.append(txt(MX+50+i*60, ty, t, 16, META))

# ─── POST CARDS ──────────────────────────────────────────────────
PX = MX + 8
PW = 280
SX = MX + 298
SW = 134

def post(y, score, sub, author, title, coms, avc, seed=False):
    h = 105
    els.append(box(PX, y, PW, h, CARD, BRD, 1, True))
    vx = PX + 10
    els.append(arr(vx+5, y+32, 0, -16, RED, 2, "triangle"))
    els.append(txt(vx, y+38, str(score), 20, "#1e1e1e"))
    els.append(arr(vx+5, y+62, 0, 14, "#d1d5db", 1, "triangle"))
    # Avatar
    els.append(ell(PX+35, y+8, 24, 24, avc, "#fff", 2,
                   label={"text": author[0].upper(), "fontSize": 12}))
    # Meta line
    mx = PX + 65
    if seed:
        # Seed badge ABOVE meta line
        els.append(box(PX+65, y+6, 65, 16, VBRD, VBRD, 0, True,
                       label={"text": "CL:SEED", "fontSize": 11}))
        els.append(txt(mx, y+26, f"m/{sub}", 16, GRN))
        els.append(txt(mx+len(sub)*9+14, y+26, author, 16, META))
    else:
        els.append(txt(mx, y+12, f"m/{sub}", 16, GRN))
        els.append(txt(mx+len(sub)*9+14, y+12, author, 16, META))
    # Title
    els.append(txt(PX+35, y+46, title, 16, "#1e293b"))
    # Comments
    els.append(txt(PX+35, y+h-22, f"{coms} comments", 14, META))

cy = MY + 72
post(cy, 89, "general", "agent_alpha", "Collective Intelligence in AI", 75, P['baseline'][0])
post(cy+115, 42, "philosophy", "agent_zeta", "Contrarian Views Strengthen", 15, P['contrarian'][0])
post(cy+230, 5, "general", "CivicLens", "AI Consensus Study...", 3, P['curious'][0], True)

# ─── SIDEBAR ─────────────────────────────────────────────────────
# Live Activity (dark)
els.append(box(SX, MY+72, SW, 150, NAV, NAV, 0, True))
els.append(txt(SX+8, MY+78, "Live Activity", 16, GRN))
activity = [
    ("alpha", "posted in m/gen..."),
    ("zeta", "commented on..."),
    ("delta", "voted on a post"),
    ("beta", "posted in m/phil..."),
]
for i, (agent, action) in enumerate(activity):
    ay = MY + 100 + i * 28
    els.append(ell(SX+10, ay, 14, 14, GRN, GRN, 0))
    els.append(txt(SX+28, ay, agent, 12, "#a3e635"))
    els.append(txt(SX+28, ay+14, action, 11, "#a3a3a3"))

# Submolts
els.append(txt(SX+8, MY+232, "Submolts", 18, "#1e1e1e"))
for i, s in enumerate(["m/general", "m/agents", "m/philosophy"]):
    sy = MY + 258 + i * 28
    els.append(ell(SX+10, sy, 18, 18, GRN, GRN, 0))
    els.append(txt(SX+34, sy, s, 16, "#1e1e1e"))

# Build for Agents CTA
els.append(box(SX, MY+348, SW, 70, "#1e1e1e", "#1e1e1e", 0, True))
els.append(txt(SX+12, MY+356, "Build for", 16, "#e5e5e5"))
els.append(txt(SX+12, MY+376, "Agents", 18, "#e5e5e5"))
els.append(box(SX+10, MY+398, SW-20, 16, RED, RED, 0, True,
               label={"text": "Get Early Access", "fontSize": 11}))

# Scroll indicator
els.append(box(MX+MW-5, MY+90, 4, 70, "#d1d5db", "#d1d5db", 0, True))

# ═══ RIGHT — Docker Agent Containers ════════════════════════════
els.append(cam(400, 300, 780, 30))

AX, AY, AW = 800, 52, 290
AH = 550
els.append(box(AX, AY, AW, AH, ABG, ABRDR, 1, True, 22))
els.append(txt(AX+65, AY+8, "Docker Agents", 20, ADARK))
els.append(txt(AX+90, AY+30, "(AI Agents)", 16, GRN))

cw, rh = 125, 85
gx, gy = 12, 10
sx, sy = AX + 14, AY + 52

for idx, (greek, name, pers) in enumerate(AGENTS):
    col, row = idx % 2, idx // 2
    ax = sx + col * (cw + gx)
    ay = sy + row * (rh + gy)
    pd, pl = P[pers]
    short = PSHORT[pers]

    els.append(box(ax, ay, cw, rh, pl, pd, 1.5, True))
    # Header strip
    els.append(box(ax, ay, cw, 24, pd, pd, 0))
    els.append(box(ax, ay+16, cw, 8, pd, pd, 0))
    els.append(txt(ax+8, ay+3, greek, 18, "#fff"))
    els.append(txt(ax+28, ay+4, short, 14, "#fff"))
    # Agent name centered in body
    els.append(txt(ax+12, ay+40, f"agent_{name}", 16, pd))

# +N
ny = sy + 4 * (rh + gy) + 5
els.append(box(AX+45, ny, AW-90, 30, "transparent", ADARK, 2, True, dash=True,
               label={"text": "...+N agents", "fontSize": 18}))

# ═══ LEFT — Experimental Variables ══════════════════════════════
els.append(cam(400, 300, -30, 30))

VX, VY, VW = 5, 52, 275
VH = 550
els.append(box(VX, VY, VW, VH, VBG, VBRD, 1, True, 22))
els.append(txt(VX+45, VY+8, "Exp. Variables", 20, VDARK))
els.append(txt(VX+50, VY+30, "(Control Panel)", 16, VMID))

def vbox(y, lbl, val, extra_fn=None):
    vh = 110
    els.append(box(VX+10, y, VW-20, vh, "#fff", "#fde68a", 1, True))
    els.append(txt(VX+22, y+8, lbl, 18, VDARK))
    els.append(txt(VX+22, y+30, val, 20, VMID))
    if extra_fn: extra_fn(y)

def ex_agents(y):
    for i in range(4):
        els.append(ell(VX+25+i*26, y+56, 20, 20, VBRD, VMID, 1))
    els.append(txt(VX+135, y+58, "...", 18, VMID))
    # Slider
    els.append(box(VX+22, y+86, 195, 6, "#fde68a", "#fde68a", 0, True))
    els.append(ell(VX+140, y+82, 14, 14, VBRD, VMID, 2))

def ex_personality(y):
    cols = [('#10B981','Ldr'), ('#EF4444','Ctr'), ('#F59E0B','Cur'), ('#06B6D4','Flw')]
    for i, (c, l) in enumerate(cols):
        els.append(box(VX+22+i*52, y+58, 44, 22, c, c, 0, True,
                       label={"text": l, "fontSize": 12}))
    els.append(txt(VX+22, y+90, "swappable", 16, VMID))

def ex_seeds(y):
    for i in range(3):
        els.append(box(VX+22+i*5, y+62-i*4, 44, 24, "#fef3c7" if i>0 else "#fff", VMID, 1, True))
    els.append(txt(VX+88, y+64, "\u2192 inject", 16, VMID))

def ex_duration(y):
    els.append(ell(VX+22, y+56, 32, 32, "transparent", VBRD, 2))
    els.append(arr(VX+38, y+72, 8, -10, VBRD, 2, None))
    els.append(txt(VX+65, y+64, "30m \u2013 4h", 16, VMID))

vy = VY + 52
vbox(vy, "AGENTS", "\u00d7N (adjustable)", ex_agents)
vbox(vy+120, "PERSONALITY", "11 archetypes", ex_personality)
vbox(vy+240, "SEED POSTS", "Quantity", ex_seeds)
vbox(vy+360, "DURATION", "t = (config)", ex_duration)

# ═══ CONNECTIONS ════════════════════════════════════════════════
els.append(cam(1200, 900, -60, -30))

# Seed injection (solid amber)
els.append(arr(280, 382, 30, -35, VBRD, 3, "arrow"))
els.append(txt(282, 352, "inject", 16, VMID))

# Variable dashed arrows
els.append(arr(280, 130, 30, 10, META, 1, "arrow", dash=True))
els.append(arr(280, 248, 30, 5, META, 1, "arrow", dash=True))
els.append(arr(280, 490, 30, 12, META, 1, "arrow", dash=True))

# Agent ↔ Moltbook (blue, bidirectional)
for ay in [160, 290, 420]:
    els.append(arr(750, ay, 50, 0, BLUE, 2, "arrow", "arrow"))
els.append(txt(758, 220, "read", 16, BLUE))
els.append(txt(758, 238, "post", 16, BLUE))
els.append(txt(758, 256, "vote", 16, BLUE))

# ═══ LEGEND ═════════════════════════════════════════════════════
ly = 620
els.append(arr(30, ly-3, 1080, 0, BRD, 1, None))
els.append(txt(30, ly+2, "Legend:", 16, "#4a5568"))

items = list(P.items())
for i, (name, (dark, _)) in enumerate(items):
    col, row = i % 4, i // 4
    lx = 30 + col * 255
    ry = ly + 24 + row * 24
    els.append(ell(lx, ry, 16, 16, dark, dark, 0))
    els.append(txt(lx+22, ry, name, 16, "#4a5568"))

cx = 900
els.append(arr(cx, ly+24, 22, 0, VBRD, 2, "arrow"))
els.append(txt(cx+28, ly+20, "Seed inject", 16, "#4a5568"))
els.append(arr(cx, ly+46, 22, 0, BLUE, 2, "arrow", "arrow"))
els.append(txt(cx+28, ly+42, "Agent interact", 16, "#4a5568"))
els.append(arr(cx, ly+68, 22, 0, META, 1, "arrow", dash=True))
els.append(txt(cx+28, ly+64, "Variable ctrl", 16, "#4a5568"))

els.append(cam(1200, 900, -60, -30))
print(json.dumps(els))
