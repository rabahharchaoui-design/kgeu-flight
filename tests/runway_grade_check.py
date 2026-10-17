# Runways item: every runway end in window.__kgeu.RWY_ENDS gives a landing grade, in free flight and
# in the landing challenges, in Arizona and in every world region. Built to catch the Sky Harbor bug:
# right now some (or all) of its six ends give no grade. Model: tests/landing_check.py (grade badge,
# SCORE.recent) and tests/rio_check.py (how a world region page is started). iPhone 15 landscape.
#
# Per end: teleport onto it (300 m past the threshold, on the landing heading, slow sink, gear down,
# flaps out) and step physics until the wheels are down; the grade badge must come on with a letter,
# SCORE.recent must gain a fresh entry naming that runway, and a leaderboard spy must see a runEnd call
# for 'free:landing'. Then the landing challenges (arc:landing, arc:landing1, a 737's arc:landing, the
# daily, and in a world region apt:<ICAO>) are flown onto K.ARC.end the same way.
#
# Usage: .venv/bin/python tests/runway_grade_check.py [out.txt]
# Prints one row per end/challenge and a final PASS/FAIL tally. All checks also go through Checks()
# so the process exit code is 0 only when everything passed.
import asyncio, sys, os
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15, Checks

ok = Checks()
STORAGE = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'}
REGIONS = ['az', 'rjtt', 'lfpg', 'sbrj']
ROWS = []   # (region, code, num, badge_on, letter, where, lb_ok)

SPY_INSTALL = """()=>{
  const K=window.__kgeu;
  if(K.LB.__spied)return;
  K.LB.__spied=true;K.LB.__calls=[];
  for(const name of ['runEnd','runStart','armFree']){
    const orig=K.LB[name];
    K.LB[name]=function(...a){K.LB.__calls.push({fn:name,board:a[0]});return orig.apply(K.LB,a);};
  }
}"""

ENDS_META = "()=>window.__kgeu.RWY_ENDS.map((e,i)=>({i:i,num:e.num,code:e.rwy.code,apt:e.rwy.apt,len:e.rwy.len}))"

# teleport onto a runway end given either an index into RWY_ENDS (kind 'i') or K.ARC.end (kind 'arc'),
# at V m/s down the runway, gentle sink, gear down, flaps out; step physics (held, no render) until the
# wheels are down or 60 frames (1 s) pass; release the hold.
LAND_JS = """([kind,i,V])=>{
  const K=window.__kgeu, e=kind==='arc'?K.ARC.end:K.RWY_ENDS[i], s=K.state();
  const gear=K.rwyFrame().gear;
  const x=e.x+e.dx*300, z=e.z+e.dz*300;
  s.pos.set(x, K.groundHeight(x,z)+gear+0.6, z);
  s.vel.set(e.dx*V, -1.0, e.dz*V);
  s.quat.setFromEuler(new THREE.Euler(0.03, -e.h, 0, 'YXZ'));
  s.w.set(0,0,0);
  s.onGround=false; s.airTime=30; s.flapIdx=3; s.gearDown=true; s.gearPos=1;
  s.ap=null; s.throttle=s.power=0;
  K.touchIn.active=false; K.snapCam();
  let n=0;
  for(;n<60;n++){ K.stepFrame(1/60); if(K.state().onGround) break; }
  K.stepFrame(0,true);
  return {onGround:K.state().onGround, crashed:K.state().crashed, n:n,
    end:{num:e.num,apt:e.rwy.apt,code:e.rwy.code}};
}"""

READ_JS = """()=>{
  const K=window.__kgeu;
  const badge={on:document.getElementById('gBadge').classList.contains('on'),
    letter:document.getElementById('gbL').textContent, text:document.getElementById('gBadge').textContent};
  const rec=(K.SCORE.recent||[])[0]||null;
  const calls=K.LB.__calls.slice(); K.LB.__calls.length=0;
  return {badge:badge, rec:rec, calls:calls};
}"""

LAST_WHEN_JS = "()=>{const r=(window.__kgeu.SCORE.recent||[])[0];return r?r.when:null;}"

CLOSE_CARDS_JS = """()=>{
  const K=window.__kgeu;
  for(const id of ['arcOv','missOv','landOv','gradeOv']){
    const el=document.getElementById(id);
    if(el&&el.classList.contains('on'))K.resClose(el);
  }
}"""


def expected_where(e, is_az):
    code = e['code']
    if code == 'LZ':
        return 'the assault strip'
    if is_az:
        if code == 'KLUF':
            return f"Luke runway {e['num']}"
        if code == 'KPHX':
            n = e['num'].lstrip('0')
            return f"Sky Harbor runway {n if n else '0'}"
        return f"{e['apt']} runway {e['num']}"   # KGEU -> Glendale
    return f"{e['apt']} runway {e['num']}"        # world region: rwy.apt is already REGION.short


async def land_and_check(pg, tag, kind, i, end_desc, V, is_az):
    """Teleport onto one runway end (RWY_ENDS[i] or K.ARC.end), step to touchdown, and check the grade."""
    before = await pg.evaluate(LAST_WHEN_JS)
    res = await pg.evaluate(LAND_JS, [kind, i, V])
    label = f"{tag} {end_desc}"
    landed = res['onGround'] and not res['crashed']
    ok(f"{label}: touches down without crashing", landed, res)
    await pg.wait_for_timeout(400)
    read = await pg.evaluate(READ_JS)
    badge, rec, calls = read['badge'], read['rec'], read['calls']
    exp_where = expected_where(res['end'], is_az)
    fresh = landed and rec is not None and rec.get('when') != before
    where_ok = fresh and exp_where.lower() in (rec.get('where') or '').lower()
    letter_ok = bool(badge['on'] and badge['letter'] and badge['letter'] in 'ABCDF')
    lb_ok = any(c['fn'] == 'runEnd' and c['board'] == 'free:landing' for c in calls)
    ok(f"{label}: grade badge on with a letter", letter_ok, badge)
    ok(f"{label}: SCORE.recent gains a fresh entry naming {exp_where!r}", where_ok, rec)
    ok(f"{label}: LB.runEnd('free:landing') called", lb_ok, calls)
    row_ok = landed and letter_ok and where_ok and lb_ok
    ROWS.append((tag, res['end']['code'], res['end']['num'], badge['on'], (rec or {}).get('letter'),
                 (rec or {}).get('where'), lb_ok, row_ok))
    return row_ok


async def free_flight_all_ends(pg, region, is_az):
    ends = await pg.evaluate(ENDS_META)
    for e in ends:
        await pg.evaluate(f"()=>{{const K=window.__kgeu;K.pick('cessna');K.pickBase('{'kgeu' if is_az else region}');K.start('final');}}")
        await pg.wait_for_timeout(300)
        await land_and_check(pg, region, 'i', e['i'], f"{e['code']} {e['num']}", 30, is_az)
    if is_az:
        # the 737, same runways as planes2 scales it for: 7L, 25R, 8 and 26 at Sky Harbor
        targets = [e for e in ends if e['code'] == 'KPHX' and e['num'] in ('07L', '25R', '08', '26')]
        for e in targets:
            await pg.evaluate("()=>{const K=window.__kgeu;K.pick('b737');K.pickBase('phx');K.start('final');}")
            await pg.wait_for_timeout(300)
            await land_and_check(pg, region + ':b737', 'i', e['i'], f"{e['code']} {e['num']}", 70, is_az)


async def challenge_land(pg, tag, board, V=30):
    res = await pg.evaluate(LAND_JS, ['arc', 0, V])
    landed = res['onGround'] and not res['crashed']
    ok(f"{tag}: touches down on the target end without crashing", landed, res)
    await pg.evaluate("()=>window.__kgeu.ff(25)")
    await pg.wait_for_timeout(600)
    seen = await pg.evaluate("()=>window.__kgeu.LB.__calls.slice()")
    arc_on = await pg.evaluate("()=>document.getElementById('arcOv').classList.contains('on')")
    board_ok = any(c['fn'] == 'runEnd' and str(c['board']).startswith(board) for c in seen)
    ok(f"{tag}: results card is up and LB.runEnd({board!r}) was called", arc_on and board_ok, seen)
    await pg.evaluate("()=>{window.__kgeu.LB.__calls.length=0;}")
    await pg.evaluate(CLOSE_CARDS_JS)
    ROWS.append((tag, '-', board, arc_on, '-', board, board_ok, arc_on and board_ok))
    return arc_on and board_ok


async def az_challenges(pg):
    await pg.evaluate("()=>{window.__kgeu.pick('cessna');window.__kgeu.pickBase('kgeu');window.__kgeu.arcStart('landing');}")
    await pg.wait_for_timeout(600)
    await challenge_land(pg, 'arc:landing (cessna, Glendale 1)', 'arc:landing')

    await pg.evaluate("()=>window.__kgeu.arcStart('landing1')")
    await pg.wait_for_timeout(600)
    await challenge_land(pg, 'arc:landing1 (cessna, Glendale 1)', 'arc:landing1')

    await pg.evaluate("()=>{window.__kgeu.pick('b737');window.__kgeu.arcStart('landing');}")
    await pg.wait_for_timeout(600)
    await challenge_land(pg, 'arc:landing (b737, Sky Harbor 7L)', 'arc:landing', V=70)

    await pg.evaluate("()=>{window.__kgeu.pick('cessna');window.__kgeu.ARC.dailyRegion='az';window.__kgeu.ARC.dailyKind='landing';window.__kgeu.arcStart('daily');}")
    await pg.wait_for_timeout(600)
    await challenge_land(pg, 'daily (az, forced landing)', 'daily')


async def world_apt_challenge(pg, region, icao):
    await pg.evaluate("()=>{window.__kgeu.pick('cessna');window.__kgeu.arcStart('apt');}")
    await pg.wait_for_timeout(600)
    await challenge_land(pg, f'apt:{icao} ({region})', f'apt:{icao}')


async def run_region(region):
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        storage = dict(STORAGE)
        is_az = region == 'az'
        if not is_az:
            storage['kgeuRegion'] = region
        pg = await page(b, url, vp=IPHONE_15, storage=storage)
        if not is_az:
            await pg.wait_for_function("()=>window.__kgeu.WORLD.ready||window.__kgeu.WORLD.err", timeout=60000)
            await pg.wait_for_timeout(1500)
        await pg.evaluate(SPY_INSTALL)

        await free_flight_all_ends(pg, region, is_az)

        if is_az:
            await az_challenges(pg)
        else:
            icao = await pg.evaluate(f"()=>window.__kgeu.REGIONS['{region}'].icao")
            await world_apt_challenge(pg, region, icao)

        audit_note = ''
        try:
            audit = await pg.evaluate("()=>window.__kgeu.rwyAudit?window.__kgeu.rwyAudit():null")
            if audit:
                bad = [r for r in audit if not r.get('fix')]
                print(f"  [rwyAudit] {region}: {len(audit)} ends audited, {len(bad)} with no runwayFix "
                      f"at their aim point: {[(r['code'], r['num']) for r in bad]}")
            else:
                audit_note = 'rwyAudit not present yet'
        except Exception as e:
            audit_note = f'rwyAudit threw: {e}'
        if audit_note:
            print(f"  [rwyAudit] {region}: {audit_note} (not failing on it)")

        ok(f'{region}: no page errors', not pg.errs, pg.errs[:5])
        await b.close()


async def main():
    only = [a for a in sys.argv[1:] if not a.startswith('-')]
    regions = only if only else REGIONS
    for region in regions:
        print(f"\n== {region} ==")
        await run_region(region)

    print("\n%-14s %-6s %-8s %-6s %-6s %-30s %-6s" % ('region', 'code', 'num', 'badge', 'letter', 'where', 'lb'))
    for tag, code, num, badge, letter, where, lb, row_ok in ROWS:
        flag = '' if row_ok else '  <-- FAIL'
        print("%-14s %-6s %-8s %-6s %-6s %-30s %-6s%s" % (tag, code, num, badge, letter, str(where)[:30], lb, flag))
    sys.exit(ok.done('runway_grade_check'))

asyncio.run(main())
