"""Write a WebVisualization object file (for import_native on the Visualization Manager) that starts on a
given visu. webvisu.template.native is a real export_native of a WebVisualization named HMI.
Usage: python make_webvisu.py <StartVisu> <out.native> [width height]"""
import os, re, sys
here = os.path.dirname(os.path.abspath(__file__))
start, out = sys.argv[1], sys.argv[2]
w, h = (sys.argv[3], sys.argv[4]) if len(sys.argv) > 4 else ('1920', '1080')
x = open(os.path.join(here, 'webvisu.template.native'), encoding='utf-8').read()
def setv(name, val):
    global x
    x, n = re.subn(r'(<Single Name="%s" Type="[^"]*">)[^<]*(</Single>)' % name, r'\g<1>%s\g<2>' % val, x)
    assert n == 1, name
setv('StartVisu', start); setv('ClientSizeX', w); setv('ClientSizeY', h)
open(out, 'w', encoding='utf-8').write(x)
