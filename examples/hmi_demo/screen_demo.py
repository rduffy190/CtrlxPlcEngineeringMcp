# Demo tank/pump screen DEMO_Main. Binds to GVL_HmiDemo (see GVL_HmiDemo.st). `vg` is injected by visugen.
W, H = 960, 540
D = 'GVL_HmiDemo'
S = f'{D}.iState'
GREY, GREEN, AMBER, RED = 0xB4B9BE, 0x22B14C, 0xFFB000, 0xE02020
HEAD, PANEL, EDGE = 0x2B3A4A, 0xFFFFFF, 0xC4CAD0
STATES = ['Idle', 'Filling', 'Full', 'Draining', 'Faulted']
FAULTS = [(0, ''), (1, 'F1  Overfill'), (2, 'F2  Pump dry run')]


def build(tpl):
    sc = vg.Screen(tpl, 'DEMO_Main', W, H)
    sc.box(0, 0, W, 64, fill=HEAD, frame=HEAD)
    sc.label(20, 10, 220, 44, 'TANK DEMO', font=28, bold=True, color=0xFFFFFF)
    sc.box(250, 10, 260, 44, textlist='TL_DemoState', text_index=S, font=22, bold=True,
           fill=0xFFFFFF, frame=0xFFFFFF, alarm=f'{S} = 4', alarm_fill=RED)
    sc.box(530, 10, 410, 44, textlist='TL_DemoFault', text_index=f'{D}.uiFault', font=20, bold=True,
           fill=RED, frame=RED, color=0xFFFFFF, invisible=f'{D}.uiFault = 0')

    for x, w, title in ((20, 280, 'Components'), (320, 300, 'Process'), (640, 300, 'Controls')):
        sc.box(x, 80, w, 440, fill=PANEL, frame=EDGE)
        sc.label(x + 15, 88, w - 30, 30, title, font=20, bold=True, color=HEAD)

    rows = [('Pump', f'{D}.bPump', GREEN, None, f'{D}.uiFault = 2'),
            ('Drain valve', f'{D}.bValve', GREEN, None, None),
            ('Level high', f'{D}.bHigh', AMBER, None, f'{D}.uiFault = 1'),
            ('Level low', f'{D}.bLow', GREEN, None, None)]
    for i, (name, on, col, warn, fault) in enumerate(rows):
        y = 130 + i * 50
        sc.circle(40, y + 2, 26, GREY, col, on)
        if fault:
            sc.circle(40, y + 2, 26, RED, RED, 'FALSE', f'NOT ({fault})')
        sc.label(80, y, 210, 30, name, font=18)
    sc.label(35, 470, 255, 40, 'Grey off, green on, red fault', font=14, color=0x606870)

    sc.label(335, 130, 150, 30, 'Level (%)', font=17)
    sc.box(485, 130, 120, 30, '%.1f', text_var=f'{D}.lrLevel', font=17, bold=True, frame=EDGE)
    sc.label(335, 175, 150, 30, 'Temperature', font=17)
    sc.box(485, 175, 120, 30, '%.1f C', text_var=f'{D}.lrTemp', font=17, bold=True, frame=EDGE)
    sc.label(335, 220, 150, 30, 'Fill count', font=17)
    sc.box(485, 220, 120, 30, '%d', text_var=f'{D}.uiFillCount', font=17, bold=True, frame=EDGE)
    sc.label(335, 280, 150, 40, 'Fill to (%)', font=17)
    sc.numeric(485, 276, 120, 44, f'{D}.lrSetpoint', '%.0f', 10, 95, 'Fill to (%)')

    bx, bw, bh = 660, 260, 60
    sc.button(bx, 130, bw, bh, 'Start fill', f'{D}.bStart', invisible=f'{S} <> 0')
    sc.button(bx, 130, bw, bh, 'Drain', f'{D}.bDrain', invisible=f'{S} <> 2')
    sc.button(bx, 210, bw, bh, 'Stop', f'{D}.bStop', invisible=f'({S} = 0) OR ({S} = 4)')
    sc.button(bx, 130, bw, bh, 'Reset fault', f'{D}.bReset', invisible=f'{S} <> 4')
    sc.button(bx, 310, bw, bh, 'Pump manual', f'{D}.bPumpManual', toggle=True, active=f'{D}.bPump',
              invisible=f'{S} <> 0')
    sc.label(bx, 400, bw, 60, 'Start/Drain/Reset show only when useful.', font=14, color=0x606870)

    return [vg.textlist(tpl, 'TL_DemoState', list(enumerate(STATES))),
            vg.textlist(tpl, 'TL_DemoFault', FAULTS), sc.entry()]
