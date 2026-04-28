#!/usr/bin/env python3
"""
Generate publication-quality SVG diagram of CivicLens experimental setup.

Usage:
    python3 scripts/generate_civiclens_diagram.py
    python3 scripts/generate_civiclens_diagram.py -o custom_output.svg
"""
import argparse, os

W, H = 1200, 800

# ─── Colors ──────────────────────────────────────────────────────────
C = {
    'title': '#2D3748', 'subtitle': '#718096', 'label': '#4A5568',
    'meta': '#94A3B8', 'border': '#E0E3E8', 'rule': '#E2E8F0',
    'var_bg': '#FFF8E1', 'var_border': '#FDE68A', 'var_icon': '#F59E0B',
    'var_icon_bg': '#FEF3C7', 'var_dark': '#92400E', 'var_mid': '#B45309',
    'var_light': '#D97706',
    'mb_header': '#1E40AF', 'mb_ui': '#3B82F6', 'mb_bg': '#F8FAFC',
    'mb_link': '#93C5FD', 'upvote': '#FF4500',
    'dk_bg': '#F0FDF4', 'dk_border': '#BBF7D0', 'dk_dark': '#166534',
    'dk_mid': '#22C55E',
    'arr_inject': '#F59E0B', 'arr_agent': '#3B82F6', 'arr_dash': '#94A3B8',
}

# Personality: (dark, light)
P = {
    'baseline':      ('#6B7280', '#E5E7EB'),
    'introspective': ('#3B82F6', '#DBEAFE'),
    'nihilist':      ('#374151', '#F3F4F6'),
    'leader':        ('#10B981', '#D1FAE5'),
    'follower':      ('#06B6D4', '#CFFAFE'),
    'contrarian':    ('#EF4444', '#FEE2E2'),
    'curious':       ('#F59E0B', '#FEF3C7'),
    'devotee':       ('#8B5CF6', '#EDE9FE'),
    'prophet':       ('#D946EF', '#FAE8FF'),
    'seeker':        ('#F97316', '#FFEDD5'),
    'skeptic':       ('#64748B', '#F1F5F9'),
}

AGENTS = [
    ('\u03b1', 'alpha', 'baseline'),
    ('\u03b2', 'beta', 'introspective'),
    ('\u03b3', 'gamma', 'nihilist'),
    ('\u03b4', 'delta', 'leader'),
    ('\u03b5', 'epsilon', 'follower'),
    ('\u03b6', 'zeta', 'contrarian'),
    ('\u03b7', 'eta', 'curious'),
    ('\u03b8', 'theta', 'baseline'),
    ('\u03b9', 'iota', 'introspective'),
    ('\u03ba', 'kappa', 'nihilist'),
]

# ─── Material Design Icon Paths (24x24 viewBox) ─────────────────────
ICONS = {
    'people': 'M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z',
    'masks': 'M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM8.5 8c.83 0 1.5.67 1.5 1.5S9.33 11 8.5 11 7 10.33 7 9.5 7.67 8 8.5 8zm8.5 6c-1.48 1.46-3.53 2-5 2s-3.52-.54-5-2h10zm-1.5-5c.83 0 1.5.67 1.5 1.5s-.67 1.5-1.5 1.5-1.5-.67-1.5-1.5.67-1.5 1.5-1.5z',
    'document': 'M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm4 18H6V4h7v5h5v11zM8 15.01h8V17H8v-1.99zm0-4h8v1.99H8V11z',
    'clock': 'M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67V7z',
    'upvote': 'M7 14l5-5 5 5z',
    'downvote': 'M7 10l5 5 5-5z',
    'comment': 'M21.99 4c0-1.1-.89-2-1.99-2H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h14l4 4-.01-18zM18 14H6v-2h12v2zm0-3H6V9h12v2zm0-3H6V6h12v2z',
    'robot': 'M20 9V7c0-1.1-.9-2-2-2h-3c0-1.66-1.34-3-3-3S9 3.34 9 5H6c-1.1 0-2 .9-2 2v2c-1.66 0-3 1.34-3 3s1.34 3 3 3v4c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2v-4c1.66 0 3-1.34 3-3s-1.34-3-3-3zM7.5 11.5c0-.83.67-1.5 1.5-1.5s1.5.67 1.5 1.5S9.83 13 9 13s-1.5-.67-1.5-1.5zM16 17H8v-2h8v2zm-1-4c-.83 0-1.5-.67-1.5-1.5S14.17 10 15 10s1.5.67 1.5 1.5S15.83 13 15 13z',
    'docker': 'M21.81 10.25c-.06-.04-.56-.43-1.64-.43-.22 0-.45.02-.68.06-.15-.77-.69-1.43-1.34-2.03l-.27-.18-.2.27c-.26.35-.46.74-.55 1.15-.15.65-.06 1.26.24 1.79-.37.17-.97.26-1.45.26H2.14l-.01.02c-.22 2.58.36 4.59 1.68 5.93 1.14 1.16 2.83 1.74 5.01 1.74 4.2 0 7.53-1.93 9.07-5.48.6.01 1.9.04 2.56-.76l.14-.2-.18-.12z',
}

# ─── SVG Helpers ─────────────────────────────────────────────────────
FONT = 'Inter, Helvetica Neue, Arial, sans-serif'
MONO = 'JetBrains Mono, SF Mono, Consolas, monospace'

def icon(key, x, y, size, fill, op=1.0):
    s = size / 24.0
    o = f' opacity="{op}"' if op < 1.0 else ''
    return f'<g transform="translate({x},{y}) scale({s})"{o}><path d="{ICONS[key]}" fill="{fill}"/></g>'

def rect(x, y, w, h, rx=0, fill='#FFF', stroke='none', sw=1, op=1.0, extra=''):
    o = f' opacity="{op}"' if op < 1.0 else ''
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{o} {extra}/>'

def txt(s, x, y, sz, fill=C['title'], wt=400, anchor='start', fam=FONT, extra=''):
    return f'<text x="{x}" y="{y}" font-family="{fam}" font-size="{sz}" font-weight="{wt}" fill="{fill}" text-anchor="{anchor}" {extra}>{s}</text>'

def circ(cx, cy, r, fill, stroke='none', sw=1):
    return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'

def ln(x1, y1, x2, y2, stroke, sw=1, da=''):
    d = f' stroke-dasharray="{da}"' if da else ''
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{sw}"{d}/>'

def pth(d, stroke, fill='none', sw=1.5, me='', ms='', da=''):
    me_a = f' marker-end="url(#{me})"' if me else ''
    ms_a = f' marker-start="url(#{ms})"' if ms else ''
    da_a = f' stroke-dasharray="{da}"' if da else ''
    return f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{me_a}{ms_a}{da_a}/>'

# ─── SVG Defs ────────────────────────────────────────────────────────
def build_defs():
    return '''<defs>
  <style type="text/css">@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&amp;family=JetBrains+Mono:wght@500&amp;display=swap');</style>
  <marker id="ah-amber" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#F59E0B"/></marker>
  <marker id="ah-blue" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#3B82F6"/></marker>
  <marker id="ah-slate" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#94A3B8"/></marker>
  <filter id="shadow" x="-4%" y="-4%" width="108%" height="112%"><feDropShadow dx="0" dy="1" stdDeviation="2.5" flood-opacity="0.08" flood-color="#000"/></filter>
</defs>'''

# ─── Title ───────────────────────────────────────────────────────────
def build_title():
    return f'''<g id="title-bar">
  {txt("CivicLens", 30, 32, 20, C['title'], 700)}
  {txt("— Experimental Setup", 148, 32, 20, C['subtitle'], 400)}
  {ln(30, 48, 1170, 48, C['rule'])}
</g>'''

# ─── Left Panel: Experimental Variables ──────────────────────────────
def build_left_panel():
    px, py, pw = 30, 58, 260
    o = []
    o.append(f'<g id="panel-variables">')
    o.append(rect(px, py, pw, 578, 12, C['var_bg'], C['var_border']))
    o.append(txt('EXPERIMENTAL VARIABLES', px+pw/2, py+22, 10, C['var_dark'], 700, 'middle'))
    o.append(txt('(Control Panel)', px+pw/2, py+35, 8, C['var_light'], 400, 'middle'))

    # Row 1: Agents ×N
    ry = py + 48
    o.append(f'<g id="var-agents">')
    o.append(rect(px+10, ry, pw-20, 120, 10, '#FFF', C['var_border'], extra='filter="url(#shadow)"'))
    o.append(circ(px+40, ry+35, 20, C['var_icon_bg'], C['var_icon'], 1.5))
    o.append(icon('people', px+26, ry+21, 28, C['var_icon']))
    o.append(txt('AGENTS', px+70, ry+26, 11, C['var_dark'], 700))
    o.append(txt('\u00d7N', px+70, ry+48, 20, C['var_mid'], 700, fam=MONO))
    o.append(txt('(adjustable)', px+108, ry+48, 9, C['var_light'], 400))
    for i in range(4):
        o.append(circ(px+75+i*20, ry+74, 7, C['var_icon'], C['var_mid'], 1))
    o.append(txt('\u2026', px+160, ry+78, 14, C['var_light'], 700))
    o.append(rect(px+65, ry+95, 160, 6, 3, C['var_border']))
    o.append(circ(px+160, ry+98, 6, C['var_icon'], C['var_mid'], 1.5))
    o.append('</g>')

    # Row 2: Personality
    ry = py + 178
    o.append(f'<g id="var-personality">')
    o.append(rect(px+10, ry, pw-20, 120, 10, '#FFF', C['var_border'], extra='filter="url(#shadow)"'))
    o.append(circ(px+40, ry+35, 20, C['var_icon_bg'], C['var_icon'], 1.5))
    o.append(icon('masks', px+26, ry+21, 28, C['var_icon']))
    o.append(txt('PERSONALITY', px+70, ry+26, 11, C['var_dark'], 700))
    o.append(txt('11 Archetypes', px+70, ry+44, 10, C['var_light'], 500))
    swatches = [('#10B981','Ldr'), ('#EF4444','Ctr'), ('#F59E0B','Cur'), ('#06B6D4','Flw')]
    for i, (col, lbl) in enumerate(swatches):
        sx = px+38+i*50
        o.append(rect(sx, ry+58, 42, 18, 4, col))
        o.append(txt(lbl, sx+21, ry+71, 7, '#FFF', 600, 'middle'))
    o.append(txt('\u2026', px+240, ry+71, 12, C['var_light'], 700))
    o.append(txt('\u2194 interchangeable', px+pw/2, ry+100, 8, C['var_mid'], 400, 'middle'))
    o.append('</g>')

    # Row 3: Seed Posts
    ry = py + 308
    o.append(f'<g id="var-seeds">')
    o.append(rect(px+10, ry, pw-20, 120, 10, '#FFF', C['var_border'], extra='filter="url(#shadow)"'))
    o.append(circ(px+40, ry+35, 20, C['var_icon_bg'], C['var_icon'], 1.5))
    o.append(icon('document', px+26, ry+21, 28, C['var_icon']))
    o.append(txt('SEED POSTS', px+70, ry+26, 11, C['var_dark'], 700))
    o.append(txt('Quantity', px+70, ry+44, 10, C['var_light'], 500))
    for i in range(3):
        o.append(rect(px+45+i*4, ry+60-i*3, 45, 26, 3, '#FFF' if i<2 else C['var_icon_bg'], C['var_mid']))
    o.append(ln(px+55, ry+68, px+78, ry+68, C['var_mid'], 1))
    o.append(ln(px+55, ry+74, px+72, ry+74, C['var_mid'], 1))
    o.append(txt('\u2192 Inject into platform', px+110, ry+78, 9, C['var_mid'], 600))
    o.append(txt('[CL:TAG] prefix labels', px+pw/2, ry+105, 8, C['var_mid'], 400, 'middle'))
    o.append('</g>')

    # Row 4: Duration
    ry = py + 438
    o.append(f'<g id="var-duration">')
    o.append(rect(px+10, ry, pw-20, 120, 10, '#FFF', C['var_border'], extra='filter="url(#shadow)"'))
    o.append(circ(px+40, ry+35, 20, C['var_icon_bg'], C['var_icon'], 1.5))
    o.append(icon('clock', px+26, ry+21, 28, C['var_icon']))
    o.append(txt('DURATION', px+70, ry+26, 11, C['var_dark'], 700))
    o.append(txt('t =', px+70, ry+48, 18, C['var_mid'], 700, fam=MONO))
    o.append(txt('(configurable)', px+110, ry+48, 9, C['var_light'], 400))
    o.append(rect(px+40, ry+68, 190, 26, 6, C['var_icon_bg'], C['var_mid']))
    o.append(txt('30 min \u2014 4 hours', px+135, ry+86, 9, C['var_dark'], 500, 'middle'))
    o.append('</g>')

    o.append('</g>')
    return '\n'.join(o)

# ─── Center Panel: Moltbook UI ───────────────────────────────────────
def build_center_panel():
    px, py, pw = 340, 58, 360
    o = []
    o.append(f'<g id="panel-moltbook">')
    o.append(rect(px, py, pw, 578, 12, C['mb_bg'], C['border'], 1.5, extra='filter="url(#shadow)"'))

    # Browser chrome
    o.append(f'<rect x="{px}" y="{py}" width="{pw}" height="38" rx="12" fill="{C["mb_header"]}"/>')
    o.append(f'<rect x="{px}" y="{py+26}" width="{pw}" height="12" fill="{C["mb_header"]}"/>')
    o.append(circ(px+18, py+19, 5, '#EF4444'))
    o.append(circ(px+34, py+19, 5, '#F59E0B'))
    o.append(circ(px+50, py+19, 5, '#22C55E'))
    o.append(txt('Moltbook', px+pw/2, py+24, 14, '#FFF', 700, 'middle'))
    o.append(txt('(Social Network Interface)', px+pw/2, py+52, 8, C['mb_link'], 400, 'middle'))

    # Sort tabs
    tabs = [('Hot', True), ('New', False), ('Rising', False), ('Top', False)]
    tx = px + 18
    for label, active in tabs:
        col = C['mb_ui'] if active else C['meta']
        o.append(txt(label, tx, py+72, 9, col, 600 if active else 400))
        if active:
            o.append(rect(tx-2, py+75, len(label)*6+4, 2, 1, C['mb_ui']))
        tx += len(label) * 6 + 20

    # Post cards
    def post_card(cid, y, av_col, author, sub, title, score, coms, time, seed=False):
        p = [f'<g id="{cid}">']
        cw = pw - 20
        p.append(rect(px+10, y, cw, 80, 8, '#FFF', '#E2E8F0'))
        # Vote gutter
        vx = px + 22
        p.append(icon('upvote', vx, y+10, 14, C['upvote']))
        p.append(txt(str(score), vx+7, y+38, 10, C['title'], 700, 'middle'))
        p.append(icon('downvote', vx, y+42, 14, '#CBD5E1'))
        # Avatar
        ax = px + 48
        p.append(circ(ax, y+24, 10, av_col, '#FFF', 1.5))
        p.append(txt(author[0].upper(), ax, y+28, 8, '#FFF', 700, 'middle'))
        # Seed badge
        if seed:
            p.append(rect(px+63, y+8, 50, 14, 3, C['arr_inject']))
            p.append(txt('CL:SEED', px+88, y+18, 7, '#FFF', 700, 'middle'))
        # Meta
        mx = px + 63
        p.append(txt(f'u/{author}', mx, y+22, 8, C['mb_ui'], 600))
        p.append(txt(f'\u00b7 s/{sub} \u00b7 {time}', mx+len(author)*5+16, y+22, 7, C['meta'], 400))
        # Title
        p.append(txt(title, px+42, y+44, 9.5, '#1E293B', 600))
        # Comment
        p.append(icon('comment', px+42, y+56, 12, C['meta']))
        p.append(txt(f'{coms} comments', px+58, y+66, 7, C['meta'], 400))
        p.append('</g>')
        return '\n'.join(p)

    cy = py + 84
    o.append(post_card('post-1', cy, P['baseline'][0],
        'agent_alpha', 'general', 'The Nature of Collective Intelligence', 42, 8, '2h'))
    o.append(post_card('post-2', cy+90, P['contrarian'][0],
        'agent_zeta', 'philosophy', 'Why Contrarian Views Strengthen Reasoning', 28, 15, '45m'))
    o.append(post_card('post-3-seed', cy+180, P['curious'][0],
        'CivicLens', 'general', 'Breaking: New Study Questions AI Consensus\u2026', 5, 3, '5m', seed=True))

    # Comment thread
    cty = cy + 272
    o.append(f'<g id="comment-thread">')
    o.append(txt('Thread', px+18, cty, 8, C['meta'], 600))
    o.append(ln(px+28, cty+6, px+28, cty+60, '#E2E8F0', 2))
    o.append(rect(px+36, cty+6, pw-56, 24, 5, '#F8FAFC', '#E2E8F0'))
    o.append(circ(px+50, cty+18, 5, P['introspective'][0]))
    o.append(txt('u/agent_beta replied\u2026', px+60, cty+22, 7, C['mb_ui'], 500))
    o.append(ln(px+46, cty+34, px+46, cty+60, '#E2E8F0', 2))
    o.append(rect(px+54, cty+36, pw-74, 24, 5, '#F8FAFC', '#E2E8F0'))
    o.append(circ(px+68, cty+48, 5, P['leader'][0]))
    o.append(txt('u/agent_delta replied\u2026', px+78, cty+52, 7, C['mb_ui'], 500))
    o.append('</g>')

    # Sidebar / communities
    sby = cty + 72
    o.append(f'<g id="sidebar">')
    o.append(rect(px+10, sby, pw-20, 150, 8, '#EFF6FF', '#BFDBFE'))
    o.append(txt('Communities (Submolts)', px+22, sby+18, 9, '#1E40AF', 600))
    for i, s in enumerate(['s/general', 's/philosophy', 's/tech', 's/science']):
        o.append(rect(px+18, sby+26+i*24, pw-56, 18, 4, '#FFF', '#BFDBFE', 0.6))
        o.append(txt(s, px+26, sby+39+i*24, 8, C['mb_ui'], 500))
    o.append(rect(px+18, sby+122, pw-56, 18, 4, '#FFF', '#BFDBFE', 0.6))
    o.append(txt('\u2026 more', px+26, sby+135, 8, C['meta'], 400))
    o.append('</g>')

    o.append('</g>')
    return '\n'.join(o)

# ─── Right Panel: Docker Agents ──────────────────────────────────────
def build_right_panel():
    px, py, pw = 770, 58, 260
    o = []
    o.append(f'<g id="panel-agents">')
    o.append(rect(px, py, pw, 578, 12, C['dk_bg'], C['dk_border']))
    o.append(txt('DOCKER AGENTS', px+pw/2, py+22, 10, C['dk_dark'], 700, 'middle'))
    o.append(txt('(AI Agents)', px+pw/2, py+35, 8, C['dk_mid'], 400, 'middle'))

    col_w, row_h, gap_x, gap_y = 108, 82, 14, 8
    sx, sy = px + 14, py + 48

    for idx, (greek, name, pers) in enumerate(AGENTS):
        col, row = idx % 2, idx // 2
        ax = sx + col * (col_w + gap_x)
        ay = sy + row * (row_h + gap_y)
        pd, pl = P[pers]
        body_h = row_h - 4

        o.append(f'<g id="agent-{name}">')
        o.append(rect(ax, ay, col_w, body_h, 8, pl, pd, 1.5, extra='filter="url(#shadow)"'))
        # Header strip
        o.append(f'<rect x="{ax}" y="{ay}" width="{col_w}" height="20" rx="8" fill="{pd}"/>')
        o.append(f'<rect x="{ax}" y="{ay+12}" width="{col_w}" height="8" fill="{pd}"/>')
        o.append(txt(greek, ax+8, ay+15, 11, '#FFF', 700))
        plabel = pers[:9]
        o.append(txt(plabel, ax+col_w-6, ay+15, 6.5, '#FFF', 400, 'end', extra='opacity="0.8"'))
        # Robot icon
        o.append(icon('robot', ax+col_w/2-11, ay+26, 22, pd, 0.5))
        # Agent name
        o.append(txt(f'agent_{name}', ax+col_w/2, ay+body_h-8, 7, pd, 500, 'middle'))
        # Docker badge
        o.append(icon('docker', ax+col_w-16, ay+body_h-16, 12, pd, 0.25))
        o.append('</g>')

    # +N box
    ny = sy + 5 * (row_h + gap_y) + 2
    o.append(f'<g id="expandable">')
    o.append(rect(px+35, ny, pw-70, 28, 8, 'none', C['dk_mid'], 1.5, extra='stroke-dasharray="6,4"'))
    o.append(txt('\u2026 +N agents', px+pw/2, ny+19, 10, C['dk_mid'], 600, 'middle', fam=MONO))
    o.append('</g>')

    o.append('</g>')
    return '\n'.join(o)

# ─── Connection Arrows ───────────────────────────────────────────────
def build_connections():
    o = []
    o.append(f'<g id="connections">')

    # Left → Center
    o.append(f'<g id="arrow-seed-injection">')
    o.append(pth('M 290,425 C 308,425 322,355 340,355', C['arr_inject'], sw=2.5, me='ah-amber'))
    o.append(txt('inject', 302, 395, 8, C['var_mid'], 600))
    o.append('</g>')

    o.append(f'<g id="arrows-var-dashed">')
    o.append(pth('M 290,140 L 340,142', C['arr_dash'], sw=1, me='ah-slate', da='5,4'))
    o.append(pth('M 290,270 C 310,270 325,210 340,210', C['arr_dash'], sw=1, me='ah-slate', da='5,4'))
    o.append(pth('M 290,555 C 310,555 325,570 340,570', C['arr_dash'], sw=1, me='ah-slate', da='5,4'))
    o.append('</g>')

    # Center → Right
    o.append(f'<g id="arrows-agent-platform">')
    for ay in [175, 310, 450]:
        o.append(pth(f'M 700,{ay} L 770,{ay}', C['arr_agent'], sw=1.5, me='ah-blue', ms='ah-blue'))
    o.append(txt('read \u00b7 post \u00b7 vote', 735, 265, 7, C['arr_agent'], 500, 'middle',
                 extra='transform="rotate(-90,735,265)"'))
    o.append('</g>')

    o.append('</g>')
    return '\n'.join(o)

# ─── Legend ──────────────────────────────────────────────────────────
def build_legend():
    ly = 658
    o = []
    o.append(f'<g id="legend">')
    o.append(ln(30, ly, 1170, ly, C['rule']))
    o.append(txt('Personality Legend', 30, ly+16, 9, C['label'], 600))

    row1 = list(P.keys())[:6]
    row2 = list(P.keys())[6:]
    for i, p in enumerate(row1):
        sx = 30 + i * 155
        o.append(circ(sx+8, ly+34, 5, P[p][0]))
        o.append(txt(p.capitalize(), sx+18, ly+38, 8, C['label'], 400))
    for i, p in enumerate(row2):
        sx = 30 + i * 155
        o.append(circ(sx+8, ly+52, 5, P[p][0]))
        o.append(txt(p.capitalize(), sx+18, ly+56, 8, C['label'], 400))

    # Connection types
    cx = 960
    o.append(ln(cx, ly+30, cx+25, ly+30, C['arr_inject'], 2))
    o.append(txt('Seed injection', cx+30, ly+34, 7, C['label'], 400))
    o.append(ln(cx, ly+44, cx+25, ly+44, C['arr_agent'], 2))
    o.append(txt('Agent interaction', cx+30, ly+48, 7, C['label'], 400))
    o.append(ln(cx, ly+58, cx+25, ly+58, C['arr_dash'], 1, '5,4'))
    o.append(txt('Variable control', cx+30, ly+62, 7, C['label'], 400))

    o.append('</g>')
    return '\n'.join(o)

# ─── Main ────────────────────────────────────────────────────────────
def generate(output):
    svg = '\n'.join([
        f'<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">',
        build_defs(),
        rect(0, 0, W, H, 0, '#FFF'),
        build_title(),
        build_left_panel(),
        build_center_panel(),
        build_right_panel(),
        build_connections(),
        build_legend(),
        '</svg>',
    ])
    os.makedirs(os.path.dirname(os.path.abspath(output)), exist_ok=True)
    with open(output, 'w', encoding='utf-8') as f:
        f.write(svg)
    print(f'Diagram → {output}')
    print(f'  open {output}')

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('-o', '--output', default='findings/entropy-collapse-scaling/diagrams/civiclens_setup.svg')
    generate(ap.parse_args().output)
