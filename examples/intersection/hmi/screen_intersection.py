# HMI for the four-way intersection example. Built by:
#   python <skill>/scripts/visugen.py screen_intersection.py build/INT_Main.export
# Bindings: GVL_Intersection (I/O) and PRG_Intersection.fbIntersection.eState (E_IntersectionState).
# `vg` (visugen) is injected by visugen.py when it runs this file.

ALLOWED_PREFIXES = ('GVL_', 'E_', 'VisuDialogs', 'PRG_')
W, H = 1920, 1080   # default HMI size: 1080p

G = 'GVL_Intersection'
S = 'PRG_Intersection.fbIntersection.eState'
FAULTED = f'{S} = E_IntersectionState.Faulted'
NOT_FAULTED = f'{S} <> E_IntersectionState.Faulted'

HEAD, PANEL, EDGE = 0x2B3A4A, 0xFFFFFF, 0xC4CAD0
ROAD, HOUSING = 0x5A5F66, 0x1E2227
RED_OFF, RED_ON = 0x4A1A1A, 0xFF2020
YEL_OFF, YEL_ON = 0x4A3A10, 0xFFC800
GRN_OFF, GRN_ON = 0x103A18, 0x22D050
GREY, RED = 0xB4B9BE, 0xE02020

STATES = ['All red (NS next)', 'North-south green', 'North-south yellow', 'All red (EW next)',
          'East-west green', 'East-west yellow', 'Faulted: flashing red']


def head(sc, x, y, vertical, red, yel, grn):
    """Signal head: dark housing and three lamps, red first (top, or left)."""
    d, pad, step = 56, 12, 68
    lamps = ((RED_OFF, RED_ON, red), (YEL_OFF, YEL_ON, yel), (GRN_OFF, GRN_ON, grn))
    if vertical:
        sc.box(x, y, d + 2 * pad, 3 * step + pad, fill=HOUSING, frame=HOUSING)
        for i, (off, on, e) in enumerate(lamps):
            sc.circle(x + pad, y + pad + i * step, d, off, on, e)
    else:
        sc.box(x, y, 3 * step + pad, d + 2 * pad, fill=HOUSING, frame=HOUSING)
        for i, (off, on, e) in enumerate(lamps):
            sc.circle(x + pad + i * step, y + pad, d, off, on, e)


def build(tpl):
    sc = vg.Screen(tpl, 'INT_Main', W, H)

    # ---- header -----------------------------------------------------------------------------
    sc.box(0, 0, W, 90, fill=HEAD, frame=HEAD)
    sc.label(30, 15, 520, 60, 'INTERSECTION', font=44, bold=True, color=0xFFFFFF)
    sc.box(600, 15, 700, 60, textlist='TL_IntersectionState', text_index=S, font=32, bold=True,
           fill=0xFFFFFF, frame=0xFFFFFF, alarm=FAULTED, alarm_fill=RED)
    sc.box(1360, 15, 530, 60, 'CONFLICT FAULT', font=32, bold=True, fill=RED, frame=RED,
           color=0xFFFFFF, invisible=f'NOT {G}.bDI_Fault')

    # ---- intersection picture (left panel 30,110 1160x940; road centre 610,580) ------------------
    sc.box(30, 110, 1160, 940, fill=0xDDE3D5, frame=EDGE)
    sc.box(490, 110, 240, 940, fill=ROAD, frame=ROAD)          # north-south road
    sc.box(30, 460, 1160, 240, fill=ROAD, frame=ROAD)          # east-west road
    LINE = 0xE8E8E8
    sc.box(607, 120, 6, 340, fill=LINE, frame=LINE)            # centre lines
    sc.box(607, 700, 6, 340, fill=LINE, frame=LINE)
    sc.box(40, 577, 450, 6, fill=LINE, frame=LINE)
    sc.box(730, 577, 450, 6, fill=LINE, frame=LINE)
    sc.label(630, 125, 100, 40, 'N', font=30, bold=True, color=0xFFFFFF)
    sc.label(630, 990, 100, 40, 'S', font=30, bold=True, color=0xFFFFFF)
    sc.label(50, 510, 60, 40, 'W', font=30, bold=True, color=0xFFFFFF)
    sc.label(1135, 510, 50, 40, 'E', font=30, bold=True, color=0xFFFFFF)

    ns = (f'{G}.bDO_RedNS', f'{G}.bDO_YellowNS', f'{G}.bDO_GreenNS')
    ew = (f'{G}.bDO_RedEW', f'{G}.bDO_YellowEW', f'{G}.bDO_GreenEW')
    head(sc, 745, 160, True, *ns)      # north approach, right of the road
    head(sc, 398, 760, True, *ns)      # south approach, left of the road
    head(sc, 130, 368, False, *ew)     # west approach, above the road
    head(sc, 860, 712, False, *ew)     # east approach, below the road

    # ---- right: signal outputs + controls -----------------------------------------------------
    sc.box(1220, 110, 670, 940, fill=PANEL, frame=EDGE)
    sc.label(1250, 125, 600, 44, 'Signal outputs', font=32, bold=True, color=HEAD)
    rows = [('NS red', ns[0], RED_ON), ('NS yellow', ns[1], YEL_ON), ('NS green', ns[2], GRN_ON),
            ('EW red', ew[0], RED_ON), ('EW yellow', ew[1], YEL_ON), ('EW green', ew[2], GRN_ON),
            ('Conflict monitor fault', f'{G}.bDI_Fault', RED_ON)]
    for i, (name, expr, on) in enumerate(rows):
        y = 190 + i * 68
        sc.circle(1255, y, 44, GREY, on, expr)
        sc.label(1320, y + 2, 540, 40, name, font=28)
    sc.label(1250, 672, 600, 32, 'Grey = off, coloured = on', font=22, color=0x606870)

    sc.box(1250, 730, 610, 3, fill=EDGE, frame=EDGE)
    sc.label(1250, 745, 600, 44, 'Controls', font=32, bold=True, color=HEAD)
    sc.button(1250, 810, 610, 90, 'Reset fault', f'{G}.bDI_Reset', font=28, invisible=NOT_FAULTED)
    sc.label(1250, 810, 610, 90, 'Reset shows when faulted', font=24, color=0x606870, invisible=FAULTED)
    sc.button(1250, 920, 610, 90, 'Simulate conflict fault', f'{G}.bDI_Fault', toggle=True,
              active=f'{G}.bDI_Fault', font=28)
    sc.label(1250, 1014, 610, 30, 'Clear the fault, then press Reset', font=22, color=0x606870,
             invisible=f'NOT {G}.bDI_Fault')

    return [
        vg.textlist(tpl, 'TL_IntersectionState', list(enumerate(STATES))),
        sc.entry(),
    ]
