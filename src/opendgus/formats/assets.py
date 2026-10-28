"""Compatibility facade + CLI: everything from crc, icl and fonts.
Usage: python -m opendgus.formats.assets info|extract|build ..."""
from .crc import *  # noqa: F401,F403
from .icl import *  # noqa: F401,F403
from .icl import _find_marker, _rare_color  # noqa: F401
from .fonts import *  # noqa: F401,F403
from .icl import JPEG_LIMIT, read_icl, build_icl, encode_icl_jpeg  # noqa: F401

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    import argparse
    import os
    ap = argparse.ArgumentParser(description='DGUS II ICL tool')
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('info'); p.add_argument('icl')
    p = sub.add_parser('extract'); p.add_argument('icl'); p.add_argument('outdir')
    p = sub.add_parser('build'); p.add_argument('srcdir'); p.add_argument('out')
    p.add_argument('--quality', type=int, default=75); p.add_argument('--subsampling', default='4:2:0')
    p.add_argument('--cpu', default='T5L1'); p.add_argument('--ids', choices=['sequential', 'leading-digits'], default='leading-digits')
    a = ap.parse_args()
    if a.cmd == 'info':
        f = read_icl(a.icl)
        print('size=%d max_id=%d crypto=%d length_field=%d crc=%04X ok=%s layout=%s icons=%d' % (
            f.file_size, f.max_id, f.crypto, f.length_field, f.crc_stored, f.crc_ok, f.layout, len(f.entries)))
        for e in f.entries.values():
            print('  id=%5d off=0x%08X %4dx%-4d hdr=%5d data=%7d' % (e.icon_id, e.offset, e.width, e.height, e.header_len, e.data_len))
    elif a.cmd == 'extract':
        f = read_icl(a.icl)
        os.makedirs(a.outdir, exist_ok=True)
        for e in f.entries.values():
            open(os.path.join(a.outdir, '%d.jpg' % e.icon_id), 'wb').write(e.jpeg())
    elif a.cmd == 'build':
        import re
        names = sorted((n for n in os.listdir(a.srcdir) if n.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif'))),
                       key=lambda s: [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', s)])
        jp = {}
        for k, n in enumerate(names):
            if a.ids == 'leading-digits':
                m = re.match(r'\d+', n)
                if not m:
                    continue
                k = int(m.group())
            jp[k] = encode_icl_jpeg(os.path.join(a.srcdir, n), quality=a.quality, subsampling=a.subsampling, cpu=a.cpu)
        open(a.out, 'wb').write(build_icl(jp, max_size=JPEG_LIMIT[a.cpu]))
        print('wrote %s (%d icons)' % (a.out, len(jp)))
