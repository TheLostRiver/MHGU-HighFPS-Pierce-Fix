"""Build the MHGU 1.4.0 high framerate pierce/ricochet fix.

After a bowgun shell processes a hit it stays still for exactly one logic tick, then waits a
fixed time (4.0 frames for pierce-type ammo, 8.0 for Normal S Lv3 ricochet) before re-arming
its attack. Game time is measured in 60fps frames, so one tick is 2.0 frames at 30fps, 1.0 at
60fps and 0.5 at 120fps. At higher frame rates the shell freezes for less time and travels
further between hits, dropping hits while passing through a monster.

The patch shortens the re-arm wait by (2.0 - dt) when dt < 2.0, which makes the distance
travelled between hits (and the shell lifetime used for critical distance) identical to 30fps.
At 30fps the game behaves exactly as before.

Usage:
    python make_patch.py [--out DIR] [--pchtxt] [--verify MAIN]

MAIN may be an uncompressed main NSO dump (as written by Eden's "Dump NSO" option) or a raw
decompressed program image. Requires the `keystone-engine` package.
"""
import argparse
import os
import struct

from keystone import Ks, KS_ARCH_ARM, KS_MODE_ARM

BUILD_ID = 'FB08F1D20FD1204FE7070672777F869B'
NSO_HEADER_SIZE = 0x100

TIMER_STORE = 0x46d410   # str r1, [r5, r0]  (r0 = 0x15d4, r1 = 4.0f pierce / 8.0f ricochet)
TIMER_RETURN = 0x46d414  # b 0x46d0ec
CAVE = 0x13f1e00         # zero padding between .text end (0x13f1dec) and .rodata (0x13f2000)

ORIGINAL = {
    TIMER_STORE: bytes.fromhex('001085e7'),
    TIMER_RETURN: bytes.fromhex('34ffffea'),
}

CAVE_SOURCE = f"""
    vmov       s0, r1              ; s0 = original wait
    vldr       s2, [r5, #0x1c]     ; s2 = shell delta time
    vmov.f32   s4, #2.0
    vcmpe.f32  s2, s4
    vmrs       APSR_nzcv, fpscr
    vsubmi.f32 s0, s0, s4          ; if dt < 2.0: wait = wait - 2.0 + dt
    vaddmi.f32 s0, s0, s2
    vmov       r1, s0
    str        r1, [r5, r0]        ; replaced instruction
    b          {TIMER_RETURN:#x}
"""


def assemble():
    ks = Ks(KS_ARCH_ARM, KS_MODE_ARM)
    hook, _ = ks.asm(f'b {CAVE:#x}', TIMER_STORE)
    cave, _ = ks.asm(CAVE_SOURCE.replace(';', '@'), CAVE)
    return [(TIMER_STORE, bytes(hook)), (CAVE, bytes(cave))]


def verify(path):
    data = open(path, 'rb').read()
    base = NSO_HEADER_SIZE if data[:4] == b'NSO0' else 0
    if data[:4] == b'NSO0' and data[0x40:0x50].hex().upper() != BUILD_ID[:32]:
        raise SystemExit('build id mismatch: this patch is for MHGU 1.4.0 (%s)' % BUILD_ID)
    for addr, expected in ORIGINAL.items():
        if data[base + addr:base + addr + len(expected)] != expected:
            raise SystemExit('unexpected bytes at %#x, wrong game version or already patched' % addr)
    if any(data[base + 0x13f1dec:base + 0x13f2000]):
        raise SystemExit('code cave is not empty')
    print('verified original bytes in', path)


def write_ips(records, path):
    ips = bytearray(b'IPS32')
    for addr, data in records:
        ips += struct.pack('>IH', addr + NSO_HEADER_SIZE, len(data)) + data
    ips += b'EEOF'
    with open(path, 'wb') as f:
        f.write(ips)


def write_pchtxt(records, path):
    lines = [f'@nsobid-{BUILD_ID}', '', '@flag offset_shift 0x100', '',
             '# High framerate pierce/ricochet fix', '@enabled']
    for addr, data in records:
        lines.append('%08X %s' % (addr, data.hex().upper()))
    lines.append('@stop')
    with open(path, 'w', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--out', default=os.path.join('mod', 'HighFPS_Pierce_Fix', 'exefs'))
    parser.add_argument('--pchtxt', action='store_true', help='also write an IPSwitch .pchtxt')
    parser.add_argument('--verify', metavar='MAIN', help='check original bytes in a main dump')
    args = parser.parse_args()

    if args.verify:
        verify(args.verify)

    records = assemble()
    os.makedirs(args.out, exist_ok=True)
    ips_path = os.path.join(args.out, BUILD_ID + '.ips')
    write_ips(records, ips_path)
    print('wrote', ips_path)
    if args.pchtxt:
        pchtxt_path = os.path.join(args.out, 'HighFPS_Pierce_Fix.pchtxt')
        write_pchtxt(records, pchtxt_path)
        print('wrote', pchtxt_path)


if __name__ == '__main__':
    main()
