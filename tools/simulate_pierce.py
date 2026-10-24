"""Tick simulation of the MHGU bowgun pierce hit logic (uShellPlw04_000 + MhHitAtk), as decompiled.

Per tick: shell move (hit processing or flight), then sHitcheck (MhHitAtk::update + collision test).
Times are in 60fps frames; dt is 2.0 at 30fps, 1.0 at 60fps and 0.5 at 120fps.
"""
import random

V0 = 75.0          # shell float param 0 for pierce (initial speed per frame)
D_DELAY = 2.0      # hit data entries 3..5: delay
A_ACTIVE = 99.0    # hit data entries 3..5: active duration
REARM_WAIT = 4.0   # reaction type 8 re-arm wait


def simulate(dt, max_hits, width, start, patched):
    pos = start
    v = V0
    count = 0
    timer = 0.0
    hit_pending = False
    enabled, delay, active, can_hit = True, D_DELAY, A_ACTIVE, True
    hits = []
    t = 0.0
    while t < 240.0 and pos < width + 4 * V0:
        t += dt
        # shell move
        if hit_pending:
            hit_pending = False
            count += 1
            if count < max_hits:
                wait = REARM_WAIT
                if patched and dt < 2.0:
                    wait = wait - 2.0 + dt
                timer = wait
            enabled = False
        else:
            if count > 0 and timer > 0.0:
                timer -= dt
                if timer <= 0.0:
                    timer = 0.0
                    enabled, delay, active, can_hit = True, D_DELAY, A_ACTIVE, True
                    v *= 0.7
            pos += v * dt
        # sHitcheck
        if enabled:
            if delay > 0.0:
                delay -= dt
                if delay <= 0.0:
                    active += delay
                    delay = 0.0
            elif active <= 0.0:
                enabled = False
            else:
                active -= dt
        if enabled and delay <= 0.0 and can_hit and 0.0 <= pos <= width:
            hits.append((round(t, 2), round(pos, 1)))
            can_hit = False
            hit_pending = True
    return hits


def average_hits(dt, max_hits, width, patched, samples=2000, seed=1):
    rnd = random.Random(seed)
    total = 0
    for _ in range(samples):
        start = -V0 * 6 - rnd.random() * V0 * 4
        total += len(simulate(dt, max_hits, width, start, patched))
    return total / samples


if __name__ == '__main__':
    print('example (Pierce Lv3, monster 700 units thick, same start):')
    for fps, dt in ((30, 2.0), (60, 1.0), (120, 0.5)):
        for patched in (False, True):
            h = simulate(dt, 5, 700.0, -500.0, patched)
            print('  %3dfps %-8s hits=%d  %s' % (fps, 'patched' if patched else 'vanilla', len(h), h))
    print()
    print('average hits over random entry phase:')
    print('  level width   30fps   60fps  60fps+fix  120fps  120fps+fix')
    for lv, mh in ((1, 3), (2, 4), (3, 5)):
        for width in (200, 400, 600, 800, 1000, 1400):
            r = [average_hits(2.0, mh, width, False), average_hits(1.0, mh, width, False),
                 average_hits(1.0, mh, width, True), average_hits(0.5, mh, width, False),
                 average_hits(0.5, mh, width, True)]
            print('  Lv%d  %5d  %6.2f  %6.2f  %9.2f  %6.2f  %10.2f' % (lv, width, *r))
