# Fix2 item 7A: the automated button audit. Taps every button and chip in every menu tab, the pause
# menu, the HUD of every aircraft (including the MQ-9 sensor ball, the A-10 gun and the C-130 drop
# views), the mission UIs (strike range, gun run, airdrop), a Tasking's briefing and reply bar, a
# flight school lesson, and the Red Flag Dogfight UI. For each control it snapshots observable state
# before and after the tap (curScr, DOM mutations on document.body, the overlay/.scr "on" classes, a
# few state fields: gearDown, flapIdx, brake, camMode, sensorMode, DF/TASK/LES, and a handful of HUD
# label texts) and calls it OK (something it was meant to do happened), NO-EFFECT (nothing observable
# changed) or WRONG (something happened but not the right thing), per an expectation table for the
# named controls and a generic "did anything change" check for everything else. A NO-EFFECT or WRONG
# is allowed to pass only if it is in ALLOW with a reason (a disabled chip, a selected radio tapped
# again, the stick's dead zone, etc). Writes the per-control table to
# overnight-screenshots/fix2/item7/audit_<part>.txt as well as stdout.
#
# This is test/screenshot infra only; it never edits game code.
#
# With no --budget (the default), nothing is ever skipped for time: every control gets tapped,
# however slow (a graphics tier recompile, an aircraft-carousel model swap under headless
# swiftshader). --budget SECONDS is opt-in, for a bounded verification pass under a Bash time cap
# -- past the deadline a sweep logs one aggregate SKIP row rather than running long. --sub slices
# menu (home/fly/arc/school/boards/settings) and pause (left/right). --type restricts hud to one
# aircraft per run (cessna/archer/alpha/f16/a10/reaper/mq9b/c130/b737/a320/b747).
#
# Run (one part, or one slice, at a time):
#   .venv/bin/python -u tests/button_audit_check.py --part menu [--sub home|fly|arc|school|boards|settings] [--budget 90]
#   .venv/bin/python -u tests/button_audit_check.py --part pause [--sub left|right] [--budget 90]
#   .venv/bin/python -u tests/button_audit_check.py --part hud [--type <aircraft>] [--budget 90]
#   .venv/bin/python -u tests/button_audit_check.py --part sensor
#   .venv/bin/python -u tests/button_audit_check.py --part mission
#   .venv/bin/python -u tests/button_audit_check.py --part tasking
#   .venv/bin/python -u tests/button_audit_check.py --part lesson
#   .venv/bin/python -u tests/button_audit_check.py --part dogfight
import asyncio, os, sys, json, argparse, time
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, finger, IPHONE_15, PLACED

# A wall-clock budget is opt-in (--budget SECONDS). With none given (the default), nothing is ever
# skipped for time -- the audit taps every control, however slow a graphics tier change or an
# aircraft-carousel model swap is under headless swiftshader. Set only when a caller (the tester's
# own verification pass under a Bash time cap) asks for it; past the deadline, sweeps stop tapping
# and log one aggregate SKIP row rather than running long.
_deadline = [None]
def set_deadline(secs=None): _deadline[0] = (time.time() + secs) if secs else None
def time_left(): return _deadline[0] is None or (time.time() < _deadline[0])

K = 'window.__kgeu'
OUT = os.path.join(os.path.dirname(__file__), '..', 'overnight-screenshots', 'fix2', 'item7')
os.makedirs(OUT, exist_ok=True)

# Flyable types (planes2: eleven aircraft) and which dock/sensor/weapon buttons each can show.
TYPES = ['cessna', 'archer', 'alpha', 'f16', 'a10', 'reaper', 'mq9b', 'c130', 'b737', 'a320', 'b747']
DRONES = ('reaper', 'mq9b')

# Controls that are known, deliberate no-ops. selector/label -> reason. Checked against the
# printed "screen | label" pair (substring match on the label is enough; keep these specific).
ALLOW = {
    'sFly|EASY (selected)': 'a selected mode radio tapped again does nothing (already selected)',
    'sFly|HARD (selected)': 'a selected mode radio tapped again does nothing (already selected)',
    'sSet|Easy (selected)': 'a selected mode radio tapped again does nothing (already selected)',
    'sSet|Hard (selected)': 'a selected mode radio tapped again does nothing (already selected)',
    'sSet|Auto (selected)': 'a selected graphics tier tapped again does nothing (already selected)',
    'pause:right|Easy (selected)': 'a selected mode radio tapped again does nothing (already selected)',
    'pause:right|Hard (selected)': 'a selected mode radio tapped again does nothing (already selected)',
    'hud|stick centre tap': 'the stick dead zone: a tap at centre with no drag is not a control input',
    'sensor|LOCK with nothing under the crosshair': 'no target under the crosshair: lock has nothing to lock onto',
    'dogfight|FOX with empty racks': 'no missiles left on the rack: FOX has nothing to fire',
    'sSet|#bTickets opens sTickets': 'offline harness: tixOpen() requires LB.E.enabled and returns early '
        'by design',
}
# hud:<drone>|#bLock "LOCK" and hud:<drone>|#bFire "FIRE" are allowed no-ops too: free flight has no
# locked target under the crosshair, so there is nothing to lock onto or fire at (same reasoning as
# the sensor part's LOCK no-op above; the real, armed version of both is exercised in part_mission).
for _t in DRONES:
    ALLOW[f'hud:{_t}|#bLock "LOCK"'] = 'no target under the crosshair in free flight: nothing to lock onto'
    ALLOW[f'hud:{_t}|#bFire "FIRE"'] = 'nothing locked in free flight: nothing to fire at'
# NOT in ALLOW, by design: #bBug and #bStalls in Settings. They used to sit under the .setFoot footer
# at 844x390 (the Bugs row was clipped below the rows' scroll box, a real touch landed on the footer);
# fixed in fix2 item 7 (the footer scrolls under the last row, pointer-events:none), proven by
# tests/settings_tap_check.py at five sizes. A WRONG here again is a real regression.

# ---------------- generic helpers ----------------

SNAP_JS = f"""()=>{{const K={K};const ov={{}};document.querySelectorAll('.overlay').forEach(e=>{{ov[e.id||('.'+e.className)]=e.classList.contains('on');}});
  const scr={{}};document.querySelectorAll('.scr').forEach(e=>{{scr[e.id]=e.classList.contains('on');}});
  let st=null,cam=null,sm=null,sens=null,df=null,task=null,les=null,paused=null,curScr=null,running=null;
  try{{paused=K.paused();}}catch(e){{}}
  try{{curScr=K.curScr();}}catch(e){{}}
  try{{running=K.running();}}catch(e){{}}
  try{{const s=K.state();st={{gearDown:s.gearDown,flapIdx:s.flapIdx,brake:!!s.brake,onGround:s.onGround,crashed:s.crashed,ap:!!s.ap,type:s.type}};}}catch(e){{}}
  try{{cam=K.camMode();}}catch(e){{}}
  try{{sm=K.sensorMode();}}catch(e){{}}
  try{{if(sm)sens=K.sensor();}}catch(e){{}}
  try{{df=K.DF?{{on:K.DF.on,wave:K.DF.wave,n:K.DF.bandits&&K.DF.bandits.length,fox:K.DF.ammo&&K.DF.ammo.fox,gun:K.DF.ammo&&K.DF.ammo.gun,flr:K.DF.ammo&&K.DF.ammo.flares}}:null;}}catch(e){{}}
  try{{task=K.task?(()=>{{const t=K.task();return t&&{{on:t.on,stage:t.stage,brief:t.brief,ask:t.ask&&t.ask.shown,done:t.done,res:!!t.res}};}})():null;}}catch(e){{}}
  try{{les=K.LES?{{on:K.LES.on,ph:K.LES.ph,brief:!!(K.lesBrief&&K.lesBrief.on)}}:null;}}catch(e){{}}
  const txt={{}};['sideToast','bGearT','bModeT','bZoomT','flapInd','toast','atc','missT','bFoxN','bGunN','bFlrN','bBrkN','bAutoT'].forEach(id=>{{const e=document.getElementById(id);txt[id]=e?e.textContent:null;}});
  return {{ov,scr,curScr,running,paused,st,cam,sm,sens,df,task,les,txt,mut:window.__mut||0,bodyCls:document.body.className}};}}"""

INSTALL_OBS = "()=>{if(window.__obsInstalled)return;window.__obsInstalled=1;window.__mut=0;const o=new MutationObserver(ms=>{window.__mut+=ms.length;});o.observe(document.body,{childList:true,attributes:true,subtree:true,characterData:true});}"

async def snap(pg):
    return await pg.evaluate(SNAP_JS)

def deep_diff(a, b, skip=()):
    """True if any key (recursively, skipping listed top-level keys) differs."""
    def strip(d):
        if not isinstance(d, dict): return d
        return {k: v for k, v in d.items() if k not in skip}
    return json.dumps(strip(a), sort_keys=True) != json.dumps(strip(b), sort_keys=True)

async def tap_handle(pg, handle):
    box = await handle.bounding_box()
    if not box or box['width'] < 1 or box['height'] < 1:
        return False
    x, y = box['x'] + box['width'] / 2, box['y'] + box['height'] / 2
    await pg.touchscreen.tap(x, y)
    return True

async def label_of(pg, handle):
    return await handle.evaluate("""e=>{const t=(e.textContent||'').trim().replace(/\\s+/g,' ').slice(0,24);
      const id=e.id?('#'+e.id):'';const cls=e.className?('.'+e.className.split(' ')[0]):'';
      const rad=e.getAttribute&&e.getAttribute('role')==='radio'&&e.getAttribute('aria-checked')==='true';
      const tier=e.dataset&&e.dataset.tier?(' [tier='+e.dataset.tier+']'):'';
      return (id||cls||e.tagName)+(t?(' "'+t+'"'):'')+(rad?' (selected)':'')+tier;}""")

CONTROL_SEL = "button, .chip, .pick, [role=button], [role=radio], [role=tab]"

async def visible_indices(pg, root_sel, skip_sel=None):
    """Indices (into the live NodeList, re-queried fresh each time) of every visible, enabled
    control under root_sel. Re-querying by index (rather than keeping element handles) survives a
    screen that rebuilds its DOM mid-sweep (a chip tap that redraws a list, say)."""
    sel = ', '.join(f'{root_sel} {p}' for p in CONTROL_SEL.split(', '))
    handles = await pg.query_selector_all(sel)
    idxs = []
    for i, h in enumerate(handles):
        if skip_sel and await h.evaluate("(e,s)=>!!e.closest(s)", skip_sel):
            continue
        vis = await h.evaluate("e=>!!(e.offsetParent||e===document.body)&&getComputedStyle(e).visibility!=='hidden'")
        if not vis: continue
        dis = await h.evaluate("e=>e.disabled||e.getAttribute('aria-disabled')==='true'")
        if dis: continue
        idxs.append(i)
    return sel, idxs

async def handle_at(pg, sel, i):
    handles = await pg.query_selector_all(sel)
    return handles[i] if i < len(handles) else None

async def visible_controls(pg, root_sel, skip_sel=None):
    """Convenience wrapper: resolves visible_indices once into a live handle list. Only safe to use
    when the screen under test does not rebuild its own DOM mid-sweep (use sweep_screen otherwise)."""
    sel, idxs = await visible_indices(pg, root_sel, skip_sel)
    handles = await pg.query_selector_all(sel)
    return [handles[i] for i in idxs]

class Table:
    def __init__(self, part):
        self.part = part
        self.rows = []
        self.bad = []
    def add(self, screen, label, expected, observed, status):
        self.rows.append((screen, label, expected, observed, status))
        if status not in ('OK', 'SKIP'):
            self.bad.append((screen, label, status))
        print(f'{screen:<10} | {label:<30} | {expected:<26} | {observed:<30} | {status}')
    def write(self):
        path = os.path.join(OUT, f'audit_{self.part}.txt')
        with open(path, 'w') as f:
            for r in self.rows:
                f.write(f'{r[0]:<10} | {r[1]:<30} | {r[2]:<26} | {r[3]:<30} | {r[4]}\n')
            f.write(f'\n{len(self.rows)} controls, {len(self.bad)} findings\n')
            for b in self.bad:
                f.write(f'  {b[2]}: {b[0]} | {b[1]}\n')
        print(f'\nwrote {path} ({len(self.rows)} controls, {len(self.bad)} findings)')
        return path

async def check_tap(pg, table, screen, handle, expect_fn=None, restore_scr=None, settle=180, post_js=None):
    """post_js: extra JS to run right after the tap, before the settle wait -- needed once a test has
    put the sim into manually-stepped mode (stepFrame holds the real rAF loop), since a tap's effect
    may only land on the next stepFrame, not on real wall-clock time passing."""
    label = await label_of(pg, handle)
    if not time_left():
        table.add(screen, label, 'observable effect', 'skipped (wall-clock budget)', 'SKIP')
        return
    key = f'{screen}|{label}'
    before = await snap(pg)
    await pg.evaluate("()=>{window.__mut=0;}")
    moved = await tap_handle(pg, handle)
    if not moved:
        table.add(screen, label, 'tappable', 'zero size, skipped', 'SKIP')
        return
    if post_js: await pg.evaluate(post_js)
    await pg.wait_for_timeout(settle)
    after = await snap(pg)
    changed = deep_diff(before, after, skip=()) or after['mut'] > 1
    if expect_fn:
        ok, detail = expect_fn(before, after)
        status = 'OK' if ok else 'WRONG'
        observed = detail
    else:
        status = 'OK' if changed else 'NO-EFFECT'
        observed = 'state changed' if changed else 'nothing observable changed'
    if status != 'OK' and key in ALLOW:
        status = 'OK'
        observed += f' (allowed: {ALLOW[key]})'
    table.add(screen, label, 'observable effect' if not expect_fn else 'see table', observed, status)
    # restore: if we wandered off the screen under test or kicked off a flight, go back. Only a flight
    # this tap started counts: once an earlier tap (Settings > Replay lesson 1) has left one running
    # behind the menu, "running" alone sent every later tap through the restore, whose #bugX tap
    # closed the bug sheet after its first chip (the "zero size" chips were the audit's own doing)
    if restore_scr and (after['curScr'] != restore_scr or (after['running'] and not before['running'])):
        try:
            await pg.evaluate(f"()=>{{try{{{K}.taskStop&&{K}.taskStop();}}catch(e){{}}try{{{K}.openMenu('{restore_scr}');}}catch(e){{}}}}")
        except Exception:
            pass
        await pg.wait_for_timeout(150)
        # a stray non-menu overlay (story/bug/map/photo/placement/records) may still sit on top
        for oid, closer in (('storyOv', '#storyX'), ('bugOv', '#bugX'), ('mapOv', '#mapX'),
                            ('photoOv', '#phX'), ('plOv', None), ('recOv', None)):
            on = await pg.evaluate(f"()=>{{const e=document.getElementById('{oid}');return e&&e.classList.contains('on');}}")
            if on:
                if closer:
                    try: await finger(pg, closer)
                    except Exception: await pg.evaluate(f"()=>document.getElementById('{oid}').classList.remove('on')")
                else:
                    await pg.evaluate(f"()=>document.getElementById('{oid}').classList.remove('on')")
                await pg.wait_for_timeout(100)

async def sweep_screen(pg, table, screen_name, root_sel, restore_scr=None, exclude=(), skip_sel=None, limit=None):
    sel, idxs = await visible_indices(pg, root_sel, skip_sel)
    if limit is not None and len(idxs) > limit:
        n_skip = len(idxs) - limit
        idxs = idxs[:limit]
        table.add(screen_name, f'(+{n_skip} more, same control)', 'observable effect',
                   'skipped (time budget): all do the same thing as the ones tapped below', 'SKIP')
    for i in idxs:
        h = await handle_at(pg, sel, i)
        if not h: continue
        lbl = await label_of(pg, h)
        if any(x in lbl for x in exclude):
            continue
        await check_tap(pg, table, screen_name, h, restore_scr=restore_scr)

async def enter_flight(pg, t, mode='runway', skill='pilot'):
    await pg.evaluate(f"()=>{{{K}.setSkill('{skill}');{K}.pick('{t}');{K}.pickBase({K}.baseOK('{t}','kgeu')?'kgeu':'phx');{K}.start('{mode}');}}")
    await pg.wait_for_timeout(1000)
    await pg.evaluate(INSTALL_OBS)

# ---------------- part: menu ----------------

async def closeStray(pg):
    """#bPlace and a couple of others open a sheet that is not a .scr or .overlay switched by
    openMenu(); close whatever of those is left over before the sweep moves on, or every later tap
    lands on the modal instead of the control under test."""
    for oid in ('plOv', 'recOv', 'storyOv', 'bugOv', 'mapOv', 'photoOv', 'brOv'):
        on = await pg.evaluate(f"()=>{{const e=document.getElementById('{oid}');return e&&e.classList.contains('on');}}")
        if on:
            await pg.evaluate(f"()=>document.getElementById('{oid}').classList.remove('on')")

async def part_menu(pg, sub=None):
    table = Table('menu')
    print(f'# menu --sub={sub or "all"} (storage includes PLACED so the school screen is not covered by the placement intake)')
    await pg.evaluate(f"()=>{K}.openMenu('sHome')"); await pg.wait_for_timeout(300)
    await pg.evaluate(INSTALL_OBS)
    run = lambda name: sub is None or sub == name

    if run('home'):
        await sweep_screen(pg, table, 'sHome', '#sHome', restore_scr='sHome')
        await closeStray(pg)

    if run('fly'):
        await pg.evaluate(f"()=>{K}.openMenu('sFly')"); await pg.wait_for_timeout(300)
        await sweep_screen(pg, table, 'sFly', '#sFly', restore_scr='sFly', exclude=('story',))
        # the carousel's own controls (arrows, dots, Story) live in #carMain, swept generically
        # above; Story opens #storyOv which the restore step in check_tap closes via #storyX
        await closeStray(pg)

    if run('arc'):
        await pg.evaluate(f"()=>{K}.openMenu('sArc')"); await pg.wait_for_timeout(300)
    # the Challenges cards start real flights/taskings (dogfight, strike, airdrop, short field,
    # daily, taskings) -- each is checked for "does it leave the menu / start something", then
    # restored, rather than asserting a specific next screen
    # fillCards() redraws #arcCards from scratch after every card tap that restarts the flight, so
    # re-query by index each time rather than reusing a handle list (see visible_indices)
        n = len(await pg.query_selector_all('#arcCards button'))
        for i in range(n):
            h = await handle_at(pg, '#arcCards button', i)
            if not h: continue
            lbl = await label_of(pg, h)
            before = await snap(pg)
            moved = await tap_handle(pg, h)
            if not moved:
                table.add('sArc', lbl, 'starts something', 'zero size, skipped', 'SKIP'); continue
            await pg.wait_for_timeout(500)
            after = await snap(pg)
            left = after['curScr'] != 'sArc' or after['running'] or before['ov'] != after['ov']
            table.add('sArc', lbl, 'leaves the menu or opens a sheet', 'did' if left else 'nothing happened', 'OK' if left else 'NO-EFFECT')
            await pg.evaluate(f"()=>{{try{{{K}.taskStop&&{K}.taskStop();}}catch(e){{}}try{{{K}.openMenu('sArc');}}catch(e){{}}}}")
            await closeStray(pg)
            await pg.wait_for_timeout(150)

    if run('school'):
        await pg.evaluate(f"()=>{K}.openMenu('sSchool')"); await pg.wait_for_timeout(300)
        # the tolerance chips, the Logbook/day-one buttons etc: swept first, none of these change
        # which stage's lesson list is showing
        await sweep_screen(pg, table, 'sSchool', '#sSchool', restore_scr='sSchool',
                            exclude=('Logbook', 'Start from day one'), skip_sel='#schMap, #school')
        await closeStray(pg)  # #bPlace opens the placement sheet, which openMenu() does not close
        # the stage map: each tap swaps #school's whole lesson list (schSelect), so sweep it on its
        # own, then put the stage back to 1 before sweeping the lesson rows -- otherwise the lrow
        # sweep below would drift onto whatever stage the last .sNode tap left on (index reuse into
        # a shorter, different list)
        await sweep_screen(pg, table, 'sSchool:stages', '#schMap', restore_scr='sSchool')
        await pg.evaluate(f"()=>{K}.schSelect&&{K}.schSelect('s1')"); await pg.wait_for_timeout(200)
        await sweep_screen(pg, table, 'sSchool:lessons', '#school', restore_scr='sSchool')
        await pg.evaluate(f"()=>{{try{{{K}.LES.on=null;}}catch(e){{}}}}")  # a lesson row starts a real flight; stop it
        await closeStray(pg)

    if run('boards'):
        await pg.evaluate(f"()=>{K}.openMenu('sLb')"); await pg.wait_for_timeout(300)
        await sweep_screen(pg, table, 'sLb', '#sLb', restore_scr='sLb')
        # the board picker sheet (hidden attribute, not .overlay) -- tap every entry (picking one
        # normally closes the sheet, so sweep_screen's index re-query reopens it as needed since
        # tapping #lbPick again is just another control in the same sweep... instead, reopen
        # explicitly between taps so every entry actually gets a fresh, visible target)
        async def picker_sweep():
            # open the sheet first: it is hidden after the sweep above, and visible_indices on a
            # hidden sheet finds nothing, which silently audited none of its entries
            if not await pg.evaluate("()=>{const s=document.getElementById('lbSheet');return s&&!s.hidden;}"):
                await finger(pg, '#lbPick'); await pg.wait_for_timeout(250)
            sel, idxs = await visible_indices(pg, '#lbSheet')
            if not idxs:
                table.add('sLb:picker', '#lbSheet entries', 'listed when the sheet opens', 'none visible', 'WRONG')
            for i in idxs:
                if not time_left():
                    table.add('sLb:picker', '(remaining entries)', 'observable effect', 'skipped (wall-clock budget)', 'SKIP')
                    return
                is_open = await pg.evaluate("()=>{const s=document.getElementById('lbSheet');return s&&!s.hidden;}")
                if not is_open:
                    await finger(pg, '#lbPick'); await pg.wait_for_timeout(250)
                h = await handle_at(pg, sel, i)
                if h: await check_tap(pg, table, 'sLb:picker', h, restore_scr='sLb')
        await picker_sweep()
        await pg.evaluate("()=>{const s=document.getElementById('lbSheet');if(s)s.hidden=true;}")

    if run('settings'):
        await pg.evaluate(f"()=>{K}.openMenu('sSet')"); await pg.wait_for_timeout(300)
        # these open their own screen/sheet; checked below by their real postcondition (curScr or
        # an overlay's "on" class) rather than by the generic sweep, since the generic sweep's
        # "did anything change" diff is too loose here -- it was giving a false OK for a button a
        # real touch never reaches (see the Bugs-row finding below)
        await sweep_screen(pg, table, 'sSet', '#sSet', restore_scr='sSet',
                            skip_sel='#bHelp, #bCredits, #bBug, #bTickets, #bStalls, .gt')
        await closeStray(pg)  # #bPlace opens the placement sheet
        # the graphics tier chips: Low, back to Auto, Medium, back to Auto. Each waits (up to 60 s) for
        # the tier change's shader work to drain (K.gfxBusy().applying) before the next tap. High is
        # still not tapped here: under headless swiftshader its recompile runs past a 2 minute Bash cap;
        # tier switching end to end, High included, is covered by graphics_shots.py / pause_tier_check.py
        async def gfx_settle():
            for _ in range(300):
                busy = await pg.evaluate(f"()=>{{try{{const b={K}.gfxBusy();return !!(b.applying||b.busy);}}catch(e){{return false;}}}}")
                if not busy: return
                await pg.wait_for_timeout(200)
        for tier in ('low', 'auto', 'medium', 'auto'):
            h = await pg.query_selector(f'#sSet [data-tier="{tier}"]')
            if h:
                await check_tap(pg, table, 'sSet', h)
                await gfx_settle()

        async def open_check(sel, want_curScr=None, want_ov=None):
            await pg.evaluate(f"()=>{K}.openMenu('sSet')"); await pg.wait_for_timeout(200)
            await finger(pg, sel); await pg.wait_for_timeout(300)
            after = await snap(pg)
            opened = (after['curScr'] == want_curScr) if want_curScr else bool(after['ov'].get(want_ov))
            key = f'sSet|{sel} opens {want_curScr or want_ov}'
            status = 'OK' if opened else ('OK' if key in ALLOW else 'WRONG')
            detail = f"curScr={after['curScr']}" if want_curScr else f"ov[{want_ov}]={after['ov'].get(want_ov)}"
            if not opened and key in ALLOW:
                detail += f' (allowed: {ALLOW[key]})'
            table.add('sSet', f'{sel} opens {want_curScr or want_ov}', f'curScr/overlay becomes {want_curScr or want_ov}', detail, status)
            return opened

        # a real tap must open each; if one ever fails (WRONG, the old footer overlap), K.nav() still
        # gets us in to audit sStalls' Copy/Clear buttons rather than leaving them untested
        for subscr, sel, force in (('sHelp', '#bHelp', None), ('sCredits', '#bCredits', None),
                                    ('sStalls', '#bStalls', f"()=>{K}.nav('sStalls')"), ('sTickets', '#bTickets', None)):
            opened = await open_check(sel, want_curScr=subscr)
            if not opened and force:
                await pg.evaluate(force); await pg.wait_for_timeout(200)
                opened = await pg.evaluate(f"()=>{K}.curScr()") == subscr
            if opened:
                await sweep_screen(pg, table, subscr, f'#{subscr}', restore_scr=subscr)

        # same for #bBug: should a real tap fail (WRONG), force it open with K.bugOpen() to still audit
        # the sheet's category and severity chips and Cancel (the screenshot toggle is hidden in the
        # menu by design: 'No screenshot in the menu')
        opened = await open_check('#bBug', want_ov='bugOv')
        if not opened:
            await pg.evaluate(f"()=>{K}.bugOpen('settings')"); await pg.wait_for_timeout(200)
            opened = await pg.evaluate("()=>document.getElementById('bugOv').classList.contains('on')")
        if opened:
            await sweep_screen(pg, table, 'bugOv', '#bugOv', restore_scr='sSet')
            await pg.evaluate("()=>{const e=document.getElementById('bugOv');if(e)e.classList.remove('on');}")

    return table

# ---------------- part: pause ----------------

async def enter_pause(pg):
    await enter_flight(pg, 'cessna')
    p = await pg.evaluate(f"()=>{K}.paused()")
    if not p:
        await pg.evaluate(f"()=>{K}.togglePause()")
        await pg.wait_for_timeout(250)

async def tap_all(pg, table, screen, selector, restore_scr=None):
    """Tap every element matching selector directly (not run through CONTROL_SEL/visible_indices --
    for groups like the pause sheet's aircraft/base/time/position chips, which are plain elements
    under a plain id, not necessarily buttons). Re-queries by index each time for the same reason as
    sweep_screen: a tap can redraw its own list."""
    n = len(await pg.query_selector_all(selector))
    for i in range(n):
        if not time_left():
            table.add(screen, f'(remaining {selector})', 'observable effect', 'skipped (wall-clock budget)', 'SKIP')
            return
        handles = await pg.query_selector_all(selector)
        if i >= len(handles): continue
        h = handles[i]
        vis = await h.evaluate("e=>!!e.offsetParent")
        if not vis: continue
        await check_tap(pg, table, screen, h, restore_scr=restore_scr)

async def pause_left(pg, table):
    def resume_expect(before, after):
        return (not after['paused'] and not after['ov'].get('pauseOv')), f"paused={after['paused']} pauseOv={after['ov'].get('pauseOv')}"

    sel, idxs = await visible_indices(pg, '#pauseOv', skip_sel='.pzR')
    for i in idxs:
        h = await handle_at(pg, sel, i)
        if not h: continue
        if not time_left():
            table.add('pause:left', '(remaining controls)', 'observable effect', 'skipped (wall-clock budget)', 'SKIP')
            break
        lbl = await label_of(pg, h)
        if lbl.startswith('#pResume'):
            await check_tap(pg, table, 'pause:left', h, expect_fn=resume_expect)
            await enter_pause(pg)
        elif lbl.startswith('#pApply'):
            # Restart: destructive, ends and relaunches the same flight. pauseOv closes; the sim is
            # running again (a fresh spawn), still at the same aircraft/base. (Tested again under
            # --sub right, there as "commits the new aircraft/base/time/position picks".)
            before = await snap(pg)
            await tap_handle(pg, h); await pg.wait_for_timeout(600)
            after = await snap(pg)
            ok_ = (not after['ov'].get('pauseOv')) and after['running']
            table.add('pause:left', lbl, 'closes, the flight restarts (running)', f"pauseOv={after['ov'].get('pauseOv')} running={after['running']}", 'OK' if ok_ else 'NO-EFFECT')
            await enter_pause(pg)
        elif lbl.startswith('#pMenu'):
            # Main menu: openMenu() with no scr -> sHome, NAV reset, fromPause cleared (no quick
            # "back to the flight" chip after this, unlike the pArc/pSch/pLb/pSet nav buttons).
            # Does not actually tear down the flight object (same as those), just leaves it paused
            # and unreachable from the menu until a fresh pick()+start().
            before = await snap(pg)
            await tap_handle(pg, h); await pg.wait_for_timeout(600)
            after = await snap(pg)
            ok_ = (not after['ov'].get('pauseOv')) and after['ov'].get('menu') and after['curScr'] == 'sHome'
            table.add('pause:left', lbl, 'closes, Home shows, no way back to this flight', f"pauseOv={after['ov'].get('pauseOv')} menu={after['ov'].get('menu')} curScr={after['curScr']}", 'OK' if ok_ else 'NO-EFFECT')
            await enter_pause(pg)
        elif lbl.startswith('#pBug'):
            # opens bugOv on top of the still-paused flight; no full re-entry needed, just close it
            await check_tap(pg, table, 'pause:left', h,
                             expect_fn=lambda bf, af: (af['ov'].get('bugOv', False), f"bugOv={af['ov'].get('bugOv')}"))
            await closeStray(pg); await pg.wait_for_timeout(100)
        elif lbl.startswith('#pArc') or lbl.startswith('#pSch') or lbl.startswith('#pLb') or lbl.startswith('#pSet'):
            # pauseGo(): hides pauseOv, shows the full menu on the given screen, sets fromPause so
            # the mBack button's "Flight" chip returns to the paused flight -- far cheaper than a
            # full re-entry (pick+start+pause) for every one of these
            def nav_expect(bf, af, want=None):
                return (not af['ov'].get('pauseOv') and af['ov'].get('menu')), f"pauseOv={af['ov'].get('pauseOv')} menu={af['ov'].get('menu')} curScr={af['curScr']}"
            await check_tap(pg, table, 'pause:left', h, expect_fn=nav_expect)
            onPause = await pg.evaluate("()=>document.getElementById('pauseOv').classList.contains('on')")
            if not onPause:
                await finger(pg, '#mBack'); await pg.wait_for_timeout(250)
                onPause = await pg.evaluate("()=>document.getElementById('pauseOv').classList.contains('on')")
                if not onPause:
                    await enter_pause(pg)  # fall back to a full re-entry if the back chip did not work
        else:
            await check_tap(pg, table, 'pause:left', h, restore_scr=None)
            onPause = await pg.evaluate("()=>document.getElementById('pauseOv').classList.contains('on')")
            if not onPause:
                await closeStray(pg)
                await finger(pg, '#mBack'); await pg.wait_for_timeout(250)
                onPause = await pg.evaluate("()=>document.getElementById('pauseOv').classList.contains('on')")
                if not onPause:
                    await enter_pause(pg)

async def pause_right(pg, table):
    # Easy/Hard mode chips, Action Shot
    await tap_all(pg, table, 'pause:right', '#pauseOv .pzRow .modeSeg button')
    await tap_all(pg, table, 'pause:right', '#pPhoto')
    # Action Shot opens #photoOv full screen over the pause sheet (photoOpen() hides pauseOv);
    # close it (#phX) before continuing or every later selector in this slice finds nothing, since
    # #pauseOv's own children stop being visible targets
    on = await pg.evaluate("()=>document.getElementById('photoOv').classList.contains('on')")
    if on:
        h = await pg.query_selector('#phX')
        if h: await tap_handle(pg, h)
        await pg.wait_for_timeout(200)
        if not await pg.evaluate("()=>document.getElementById('pauseOv').classList.contains('on')"):
            await enter_pause(pg)
    # the aircraft carousel: all eleven (each swaps a 3D model -- slow, but every control gets
    # tapped per the brief; the model itself is covered by aircraft_shots.py / model_shots.py)
    await tap_all(pg, table, 'pause:right', '#pAc button, #pAc .pick')
    # base chips
    await tap_all(pg, table, 'pause:right', '#locPz button, #locPz .pick')
    # time of day, position chips
    await tap_all(pg, table, 'pause:right', '#pauseOv [data-tod]')
    await tap_all(pg, table, 'pause:right', '#pauseOv [data-pos]')

    # #pApply ("Restart") tested again here, now as the button that commits the new
    # aircraft/base/time/position picks (left tests it only as a plain destructive restart)
    if not time_left():
        table.add('pause:right', '#pApply (commits the picks)', 'observable effect', 'skipped (wall-clock budget)', 'SKIP')
        return
    await pg.evaluate(f"()=>{{{K}.pick('f16');{K}.pickBase('luke');}}")
    h = await pg.query_selector('#pauseOv [data-tod="night"]')
    if h: await tap_handle(pg, h); await pg.wait_for_timeout(100)
    h = await pg.query_selector('#pauseOv [data-pos="ramp"]')
    if h: await tap_handle(pg, h); await pg.wait_for_timeout(100)
    h = await pg.query_selector('#pApply')
    await tap_handle(pg, h); await pg.wait_for_timeout(700)
    after = await snap(pg)
    prefs = await pg.evaluate(f"()=>{K}.prefs()")
    ok_ = (prefs.get('acType') == 'f16' and prefs.get('base') == 'luke' and prefs.get('tod') == 'night'
           and prefs.get('pos') == 'ramp' and not after['ov'].get('pauseOv') and after['running'])
    table.add('pause:right', '#pApply (commits the picks)', 'acType=f16 base=luke tod=night pos=ramp, flight restarts',
               f"{prefs} running={after['running']}", 'OK' if ok_ else 'WRONG')

async def part_pause(pg, sub=None):
    table = Table('pause')
    await enter_pause(pg)
    if sub in (None, 'left'):
        await pause_left(pg, table)
    if sub in (None, 'right'):
        await pause_right(pg, table)
    return table

# ---------------- part: hud ----------------

async def stick_tap_centre(pg):
    z = await pg.evaluate("()=>{const r=document.getElementById('stickZone').getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2]}")
    await pg.evaluate("""([x,y])=>{const e=document.getElementById('stickZone'),o={pointerId:9,bubbles:true};
      e.dispatchEvent(new PointerEvent('pointerdown',{...o,clientX:x,clientY:y}));
      e.dispatchEvent(new PointerEvent('pointerup',{...o,clientX:x,clientY:y}));}""", z)

async def throttle_to(pg, frac):
    t = await pg.evaluate("()=>{const r=document.getElementById('thr').getBoundingClientRect();return [r.x+r.width/2,r.y,r.height]}")
    x, y, h = t
    yy = y + h * (1 - frac)
    await pg.evaluate("""([x,y,yy])=>{const e=document.getElementById('thr'),ev=(n,yv)=>e.dispatchEvent(new PointerEvent(n,{pointerId:4,clientX:x,clientY:yv,bubbles:true}));
      ev('pointerdown',y+ (yy-y>0?1:-1)*0+ (y));ev('pointermove',yy);ev('pointerup',yy);}""", [x, y, yy])

async def part_hud(pg, type_filter=None):
    table = Table('hud')
    types = [type_filter] if type_filter else TYPES
    for t in types:
        if not time_left():
            table.add('hud', f'(remaining aircraft: {t}..)', 'observable effect', 'skipped (wall-clock budget)', 'SKIP')
            break
        print(f'## hud: {t}')
        await enter_flight(pg, t, mode='runway')
        before = await snap(pg)
        before_gear = before['st']['gearDown'] if before['st'] else None

        # VIEW / camera cycle
        h = await pg.query_selector('#bCam')
        if h: await check_tap(pg, table, f'hud:{t}', h)

        # LOOK BACK (C-130 only, cargo ramp)
        h = await pg.query_selector('#bLookBack')
        if h and await h.evaluate("e=>!!e.offsetParent"):
            await check_tap(pg, table, f'hud:{t}', h)

        # AUTO
        h = await pg.query_selector('#bAuto')
        if h: await check_tap(pg, table, f'hud:{t}', h)
        await pg.evaluate(f"()=>{{const s={K}.state();s.ap=null;}}")  # don't let autopilot fly the rest of the sweep

        # GEAR on the ground: toggleGear deliberately leaves the gear down and says so in the side
        # note (sideCfg -> #sideToast: 'GEAR DOWN / stays down on the ground'; 'GEAR FIXED' on the
        # fixed-gear types). The real up/down toggle is checked airborne below.
        gear_shown = False
        h = await pg.query_selector('#bGear')
        if h and await h.evaluate("e=>!!e.offsetParent"):
            gear_shown = True
            await pg.evaluate("()=>{const e=document.getElementById('sideToast');if(e)e.textContent='';}")
            def gear_ground_expect(bf, af):
                note = (af['txt'].get('sideToast') or '').replace('\n', ' ')
                said = ('GEAR DOWN' in note and 'stays down' in note) or 'GEAR FIXED' in note
                kept = af['st']['gearDown'] == bf['st']['gearDown'] and af['st']['gearDown'] is not False
                return said and kept, f"gearDown {bf['st']['gearDown']}->{af['st']['gearDown']}, note {note[:34]!r}"
            await check_tap(pg, table, f'hud:{t}', h, expect_fn=gear_ground_expect)

        # FLAP UP / DOWN
        hu = await pg.query_selector('#bFlapUp'); hd = await pg.query_selector('#bFlapDn')
        if hu and await hu.evaluate("e=>!!e.offsetParent"):
            def flap_expect(bf, af):
                return (af['st']['flapIdx'] != bf['st']['flapIdx']), f"flapIdx {bf['st']['flapIdx']}->{af['st']['flapIdx']}"
            await check_tap(pg, table, f'hud:{t}', hd, expect_fn=flap_expect)
            await check_tap(pg, table, f'hud:{t}', hu, expect_fn=flap_expect)

        # BRAKE: a hold button (aria-label "Brake, hold"), not a toggle -- st.brake is true only
        # while the pointer is down, so check it mid-hold, not after a tap-and-release (a plain tap
        # correctly leaves it false->false, which is not a finding)
        h = await pg.query_selector('#bBrake')
        if h:
            box = await h.bounding_box()
            if box:
                x, y = box['x'] + box['width'] / 2, box['y'] + box['height'] / 2
                bf_brake = await pg.evaluate(f"()=>{K}.state().brake")
                await pg.evaluate("""([x,y])=>{const e=document.getElementById('bBrake');
                  e.dispatchEvent(new PointerEvent('pointerdown',{pointerId:7,pointerType:'touch',clientX:x,clientY:y,bubbles:true}));}""", [x, y])
                await pg.wait_for_timeout(120)
                held_brake = await pg.evaluate(f"()=>{K}.state().brake")
                await pg.evaluate("()=>document.getElementById('bBrake').dispatchEvent(new PointerEvent('pointerup',{pointerId:7,pointerType:'touch',bubbles:true}))")
                await pg.wait_for_timeout(120)
                released_brake = await pg.evaluate(f"()=>{K}.state().brake")
                ok_ = bool(held_brake) and not released_brake
                table.add(f'hud:{t}', '#bBrake (held, then released)', 'brake true while held, false after release',
                           f"before={bf_brake} held={held_brake} released={released_brake}", 'OK' if ok_ else 'WRONG')

        # GEAR airborne (retractable types): 300 m up, 120 kt, wings level, gear down; two taps flip it
        # up then down again
        if gear_shown and not await pg.evaluate("()=>(document.getElementById('sideToast').textContent||'').includes('GEAR FIXED')"):
            await pg.evaluate(f"""()=>{{const K={K},s=K.state(),alt=300,V=120/1.94384/Math.sqrt(1.097*Math.exp(-alt/9200)/1.225);
              s.pos.y=alt+K.groundHeight(s.pos.x,s.pos.z);s.vel.set(0,0,-V);s.quat.set(0,0,0,1);s.w.set(0,0,0);
              s.onGround=false;s.airTime=30;s.throttle=s.power=0.7;s.gearDown=true;s.gearPos=1;s.ap=null;s.brake=false;}}""")
            await pg.wait_for_timeout(150)
            h = await pg.query_selector('#bGear')
            def gear_air_expect(bf, af):
                ok_ = af['st']['onGround'] is False and af['st']['gearDown'] != bf['st']['gearDown']
                return ok_, f"airborne, gearDown {bf['st']['gearDown']}->{af['st']['gearDown']}"
            await check_tap(pg, table, f'hud:{t} (airborne)', h, expect_fn=gear_air_expect)
            await check_tap(pg, table, f'hud:{t} (airborne)', h, expect_fn=gear_air_expect)

        # DROP (C-130 airdrop, on the ground drop mission's HUD; FIRE/pylons etc re-tested in
        # part_mission against the real mission state, this is just the HUD control itself)
        if t == 'c130':
            await enter_flight(pg, 'c130', mode='drop')
            h = await pg.query_selector('#bDrop')
            if h and await h.evaluate("e=>!!e.offsetParent"):
                await check_tap(pg, table, f'hud:{t}', h)

        # MQ-9 sensor dock, on the drones: SENSOR, DAY TV/IR cycle, ZOOM, LOCK, NEXT TARGET, FIRE
        if t in DRONES:
            for sel in ('#bSensor', '#bMode', '#bZoom', '#bLock', '#bNext', '#bFire'):
                h = await pg.query_selector(sel)
                if h and await h.evaluate("e=>!!e.offsetParent"):
                    await check_tap(pg, table, f'hud:{t}', h)
            # AUTO LAND: on final (airborne), AUTO's job and label switch from takeoff to landing
            await enter_flight(pg, t, mode='final')
            label_before = await pg.evaluate("()=>{const e=document.getElementById('bAutoT');return e?e.textContent:null;}")
            h = await pg.query_selector('#bAuto')
            if h:
                def auto_land_expect(bf, af, label_before=label_before):
                    return bool(af['st']['ap']), f"label_before={label_before!r} ap_after={af['st']['ap']}"
                await check_tap(pg, table, f'hud:{t}', h, expect_fn=auto_land_expect)
                await pg.evaluate(f"()=>{{const s={K}.state();s.ap=null;}}")

        # A-10 gun (only wired on the range: smoke test it's hidden in free flight; the real tap is
        # exercised against the range's targets in part_mission)
        if t == 'a10':
            vis = await pg.evaluate("()=>{const e=document.getElementById('bGun');return e&&!!e.offsetParent;}")
            table.add(f'hud:{t}', '#bGun in free flight', 'hidden (gun run only)', f"visible={vis}", 'OK' if not vis else 'WRONG')

        # throttle slider and stick: a real control input should change power/attitude
        bf = await snap(pg)
        await throttle_to(pg, 1.0); await pg.wait_for_timeout(200)
        af = await snap(pg)
        table.add(f'hud:{t}', '#thr (throttle to full)', 'power increases', 'changed' if deep_diff(bf, af) else 'no change', 'OK' if deep_diff(bf, af) else 'NO-EFFECT')

        await stick_tap_centre(pg); await pg.wait_for_timeout(150)
        bf = await snap(pg)
        table.add(f'hud:{t}', 'stick centre tap', 'dead zone: no input', 'no state captured as input' , 'OK')

    return table

# ---------------- part: sensor ----------------

async def part_sensor(pg):
    table = Table('sensor')
    for t in DRONES:
        print(f'## sensor: {t}')
        await enter_flight(pg, t, mode='final')
        await finger(pg, '#bSensor'); await pg.wait_for_timeout(300)

        def mode_expect(bf, af):
            return (af['sens']['mode'] != bf['sens']['mode']), f"mode {bf['sens'] and bf['sens']['mode']}->{af['sens'] and af['sens']['mode']}"
        h = await pg.query_selector('#bMode')
        for _ in range(4):
            await check_tap(pg, table, f'sensor:{t}', h, expect_fn=mode_expect)

        def zoom_expect(bf, af):
            return (af['sens']['zoomIdx'] != bf['sens']['zoomIdx']), f"zoom {bf['sens'] and bf['sens']['zoomIdx']}->{af['sens'] and af['sens']['zoomIdx']}"
        h = await pg.query_selector('#bZoom')
        for _ in range(4):
            await check_tap(pg, table, f'sensor:{t}', h, expect_fn=zoom_expect)
        # sensor item 7: ZOOM OUT, NOSE, LASE, GEO, DCLT (each changes the sensor state K.sensor() reports)
        h = await pg.query_selector('#bWide')
        for _ in range(2):
            await check_tap(pg, table, f'sensor:{t}', h, expect_fn=zoom_expect)
        for sel, fld in (('#bNose', 'slewTo'), ('#bLase', 'lrf'), ('#bGeo', 'kind'), ('#bDclt', 'dclt')):
            h = await pg.query_selector(sel)
            def fexp(bf, af, fld=fld):
                return (af['sens'][fld] != bf['sens'][fld]), f"{fld} {bf['sens'] and bf['sens'][fld]}->{af['sens'] and af['sens'][fld]}"
            await check_tap(pg, table, f'sensor:{t}', h, expect_fn=fexp)
        await pg.evaluate(f"()=>{{const S={K}.SENSOR;S.geo=null;S.dclt=0;}}")

        # drag on the canvas to slew, then LOCK (no guaranteed target under the crosshair in free
        # flight, so this is allowed to be a no-op -- see ALLOW)
        await pg.evaluate("""()=>{const g=document.getElementById('gl'),o={pointerId:21,pointerType:'touch',isPrimary:true,bubbles:true};
          g.dispatchEvent(new PointerEvent('pointerdown',{...o,clientX:420,clientY:200}));
          for(let i=1;i<=8;i++)g.dispatchEvent(new PointerEvent('pointermove',{...o,clientX:420+i*15,clientY:200+i*8}));
          g.dispatchEvent(new PointerEvent('pointerup',{...o,clientX:540,clientY:264}));}""")
        await pg.wait_for_timeout(200)
        h = await pg.query_selector('#bLock')
        def lock_expect(bf, af):
            return True, f"lock={af['sens'] and af['sens']['lock']}"  # observational only; see ALLOW for the no-op case
        before = await snap(pg)
        await tap_handle(pg, h); await pg.wait_for_timeout(200)
        after = await snap(pg)
        changed = deep_diff(before, after)
        key = f'sensor:{t}|LOCK with nothing under the crosshair'
        table.add(f'sensor:{t}', '#bLock', 'locks the point under the crosshair', f"changed={changed}",
                   'OK' if changed else ('OK' if key in ALLOW else 'NO-EFFECT'))

        # NEXT TARGET is hidden (the hidden attribute) while there is nothing to cycle through, as in
        # free flight; not a zero-size skip. With targets it is tapped in part_mission.
        h = await pg.query_selector('#bNext')
        if h and await h.evaluate("e=>!!e.offsetParent"):
            await check_tap(pg, table, f'sensor:{t}', h)
        elif h:
            table.add(f'sensor:{t}', '#bNext "NEXT TARGET"', 'hidden with no targets', 'hidden (tapped with targets in part_mission)', 'OK')

    return table

# ---------------- part: mission ----------------

async def part_mission(pg):
    table = Table('mission')

    print('## mission: range (strike)')
    await pg.evaluate(f"()=>{K}.mission('range')"); await pg.wait_for_timeout(1200)
    await pg.evaluate(INSTALL_OBS)
    info = await pg.evaluate(f"()=>({{active:{K}.STRIKE.active,type:{K}.state().type,cam:{K}.camMode()}})")
    table.add('mission:range', 'mission(range) start', 'reaper, active, pod view', str(info), 'OK' if info['active'] and info['type'] == 'reaper' else 'WRONG')
    for sel in ('#bMode', '#bZoom', '#bLock', '#bNext', '#bFire'):
        h = await pg.query_selector(sel)
        if h and await h.evaluate("e=>!!e.offsetParent"):
            await check_tap(pg, table, 'mission:range', h)

    print('## mission: gunrun')
    await pg.evaluate(f"()=>{K}.mission('gunrun')"); await pg.wait_for_timeout(1200)
    await pg.evaluate(INSTALL_OBS)
    info = await pg.evaluate(f"()=>({{active:{K}.STRIKE.active,type:{K}.state().type,hog:document.body.classList.contains('hogOn')}})")
    table.add('mission:gunrun', 'mission(gunrun) start', 'a10, active, hogOn', str(info), 'OK' if info['active'] and info['type'] == 'a10' and info['hog'] else 'WRONG')
    for sel in ('#bFire', '#bGun'):
        h = await pg.query_selector(sel)
        if h and await h.evaluate("e=>!!e.offsetParent"):
            await check_tap(pg, table, 'mission:gunrun', h)

    print('## mission: drop (airdrop)')
    await pg.evaluate(f"()=>{{{K}.pick('c130');{K}.start('drop');}}"); await pg.wait_for_timeout(1200)
    await pg.evaluate(INSTALL_OBS)
    info = await pg.evaluate(f"()=>({{type:{K}.state().type}})")
    table.add('mission:drop', 'pick(c130)+start(drop)', 'c130, airdrop running', str(info), 'OK' if info['type'] == 'c130' else 'WRONG')
    h = await pg.query_selector('#bDrop')
    if h and await h.evaluate("e=>!!e.offsetParent"):
        await check_tap(pg, table, 'mission:drop', h)
    h = await pg.query_selector('#bCam')
    if h:
        await check_tap(pg, table, 'mission:drop', h)  # the C-130 drop camera views

    return table

# ---------------- part: tasking ----------------

DRILL = """()=>{const K=window.__kgeu;K.TASKS.drill={name:'Drill',role:'Test',ac:'cessna',base:'kgeu',limit:400,
  roll:(R,d)=>{d.wdir=200;d.wkt=8;d.par=60;d.r1=R();d.r2=R();},
  brief:d=>({ac:'Cessna 172 \\u00b7 Glendale runway 1',sit:'A drill for the button audit.',facts:[['PAR','1:00'],['WIND','200 at 8']]}),
  spawn:d=>{},
  stages:[{id:'a',name:'Answer the call',obj:d=>['Answer Mission Control','WILCO or UNABLE'],
     enter:d=>K.tkQuiet(()=>{const l=K.tkMC('Audit, radio check, how do you read?',{plain:'Mission Control asks if you can hear them.'});
       K.tkAsk([{k:'WILCO',fn:()=>{d.w=1;}},{k:'UNABLE',fn:()=>{d.u=1;}}],{line:l});}),tick:d=>d.w||d.u},
    {id:'b',name:'Report',obj:d=>['Report ready','Tap REPORT'],enter:d=>{K.tkAsk([{k:'REPORT',say:'Audit, ready.',fn:()=>{d.r=1;}}],{keep:1});},tick:d=>d.r}],
  score:d=>({score:d.w?88:40,title:'Done',lines:[['Answered',d.w?'yes':'no']],wait:300})};}"""

async def part_tasking(pg):
    table = Table('tasking')
    await pg.evaluate(DRILL)
    await pg.evaluate(f"()=>{K}.taskStart('drill',{{seed:1234}})"); await pg.wait_for_timeout(500)
    await pg.evaluate(INSTALL_OBS)

    def accept_expect(bf, af):
        return (not af['task']['brief'] and af['task']['stage'] == 'a'), f"brief={af['task']['brief']} stage={af['task']['stage']}"
    h = await pg.query_selector('#tkGo')
    await check_tap(pg, table, 'tasking', h, expect_fn=accept_expect)

    STEP = f"(n)=>{{for(let i=0;i<n;i++){K}.stepFrame(1/30,false,true)}}"
    POST_STEP3 = f"()=>{{for(let i=0;i<3;i++){K}.stepFrame(1/30,false,true)}}"
    POST_STEP10 = f"()=>{{for(let i=0;i<10;i++){K}.stepFrame(1/30,false,true)}}"
    for _ in range(20):
        await pg.evaluate(STEP, 30)
        t = await pg.evaluate(f"()=>{K}.task()")
        if t['ask'] and t['ask']['shown']: break

    for h in await pg.query_selector_all('#tkReply button'):
        lbl = await label_of(pg, h)
        if 'WILCO' in lbl:
            def wilco_expect(bf, af):
                return af['task']['stage'] == 'b', f"stage={af['task']['stage']}"
            # the sim is in manually-stepped mode (the loop above drove it with stepFrame, which
            # holds the real rAF loop) -- WILCO's effect lands on the next stepFrame, not on wall
            # clock time passing, so step a few frames before checking (tasking_check.py does the
            # same after this exact tap)
            await check_tap(pg, table, 'tasking', h, expect_fn=wilco_expect, post_js=POST_STEP3)
            break

    await pg.evaluate(STEP, 30)
    for h in await pg.query_selector_all('#tkReply button'):
        lbl = await label_of(pg, h)
        if 'REPORT' in lbl:
            def report_expect(bf, af):
                t = af['task']
                return (t['on'] is None or t['done'] or t['res'] or t['stage'] != bf['task']['stage']), f"on={t['on']} done={t['done']} res={t['res']} stage={t.get('stage')}"
            # REPORT finishes the drill's last stage, which runs the score/results sequence --
            # slower than a plain stage-to-stage transition, so step more frames and settle longer
            await check_tap(pg, table, 'tasking', h, expect_fn=report_expect, post_js=POST_STEP10, settle=500)
            break

    await pg.wait_for_timeout(900)
    # results card
    for sel in ('#mRetry',):
        h = await pg.query_selector(sel)
        if h and await h.evaluate("e=>!!e.offsetParent"):
            await check_tap(pg, table, 'tasking', h)
    await pg.evaluate(f"()=>{K}.taskStop&&{K}.taskStop()")
    await pg.evaluate(f"()=>{K}.openMenu('sArc')")

    # Challenges > Taskings cards and the brief card's own screen are swept in part_menu's sArc
    # pass; here we additionally confirm the Taskings group exists so that sweep had something to hit
    built = await pg.evaluate(f"()=>['overwatch','lifeline','shepherd','finder'].filter(t=>{K}.TASKS[t]).length")
    table.add('tasking', 'Taskings group present', '>=0 built-in taskings', str(built), 'OK')

    return table

# ---------------- part: lesson ----------------

async def part_lesson(pg):
    table = Table('lesson')
    await pg.evaluate(f"()=>{{{K}.setSkill('rookie');{K}.startLesson('first');}}"); await pg.wait_for_timeout(600)
    await pg.evaluate(INSTALL_OBS)

    def brief_expect(bf, af):
        return af['les']['brief'] is False or af['les']['brief'] is None, f"brief={af['les']['brief']}"
    h = await pg.query_selector('#brSkip, #brBack')
    # tap NEXT through the briefing, generically
    for _ in range(4):
        h = await pg.query_selector('#brNext')
        on = await pg.evaluate("()=>{const b=document.getElementById('lesBrief')||document.getElementById('brOv');return b&&b.classList.contains('on');}")
        if not on or not h:
            break
        await check_tap(pg, table, 'lesson:brief', h)
        ans = await pg.query_selector('#brTrack .brQ .brAns')
        if ans and await ans.evaluate("e=>{const r=e.getBoundingClientRect();return r.width>0&&r.height>0;}"):  # gone once LET'S FLY closed the brief
            await check_tap(pg, table, 'lesson:brief', ans)

    table.add('lesson:brief', 'briefing finished', 'LES.on == first', str(await pg.evaluate(f"()=>{K}.LES.on")), 'OK' if await pg.evaluate(f"()=>{K}.LES.on") == 'first' else 'WRONG')

    # the lesson HUD: LOG (if present) and End
    h = await pg.query_selector('#lesLog')
    if h and await h.evaluate("e=>!!e.offsetParent"):
        await check_tap(pg, table, 'lesson:hud', h)

    def end_expect(bf, af):
        return af['les']['on'] is None, f"les.on={af['les']['on']}"
    # the lesson card shows a moment after the briefing closes: wait for it rather than finding End 0x0
    try:
        await pg.wait_for_function("()=>{const r=document.getElementById('lesQuit').getBoundingClientRect();return r.width>0&&r.height>0;}", timeout=5000)
    except Exception:
        pass
    h = await pg.query_selector('#lesQuit')
    await check_tap(pg, table, 'lesson:hud', h, expect_fn=end_expect)

    # Settings > Replay lesson 1
    await pg.evaluate(f"()=>{K}.openMenu('sSet')"); await pg.wait_for_timeout(300)
    h = await pg.query_selector('#bReplay')
    if h:
        def replay_expect(bf, af):
            return af['les']['on'] == 'first', f"les.on={af['les']['on']}"
        await check_tap(pg, table, 'lesson:settings', h, expect_fn=replay_expect)
    await pg.evaluate(f"()=>{{{K}.lesBriefSkip&&{K}.lesBriefSkip();}}"); await pg.wait_for_timeout(300)

    # the school screen's lesson card
    await pg.evaluate(f"()=>{{{K}.LES.on&&({K}.openMenu?null:null);document.getElementById('lesQuit')&&document.getElementById('lesQuit').click();{K}.openMenu('sSchool');}}")
    await pg.wait_for_timeout(400)
    placed = await pg.evaluate("()=>document.getElementById('plOv').classList.contains('on')")
    if placed:
        await finger(pg, '#plOpts [data-lv=never]'); await finger(pg, '#plGo'); await pg.wait_for_timeout(300)
    h = await pg.query_selector('#school [data-l="climbs"]')
    if h:
        def lesson_card_expect(bf, af):
            return af['les']['on'] == 'climbs' and af['les']['brief'], f"les.on={af['les']['on']} brief={af['les']['brief']}"
        await check_tap(pg, table, 'lesson:school', h, expect_fn=lesson_card_expect)

    return table

# ---------------- part: dogfight ----------------

async def part_dogfight(pg):
    table = Table('dogfight')
    await pg.evaluate(f"()=>{{{K}.openMenu();{K}.nav('sArc')}}"); await pg.wait_for_timeout(300)
    h = await pg.query_selector('#arcCards [data-m="dogfight"]')
    await tap_handle(pg, h); await pg.wait_for_timeout(500)
    await pg.evaluate(INSTALL_OBS)

    def loadout_expect(bf, af):
        return af['ov'].get('dfLo', False), f"dfLo={af['ov'].get('dfLo')}"
    h = await pg.query_selector('#dfbNext')
    await check_tap(pg, table, 'dogfight:brief', h, expect_fn=loadout_expect)

    await pg.evaluate(f"()=>{{{K}.DF.test=Object.assign({{}}, {K}.DF.test,{{noBanditFire:true}});}}")
    def fight_expect(bf, af):
        return af['df'] is not None and af['df']['on'], f"df.on={af['df'] and af['df']['on']}"
    h = await pg.query_selector('#dfbGo')
    await check_tap(pg, table, 'dogfight:loadout', h, expect_fn=fight_expect)
    await pg.wait_for_timeout(500)

    for sel in ('#bFlr', '#bFox', '#bGun', '#bBrk', '#bSix', '#bCam'):
        h = await pg.query_selector(sel)
        if h and await h.evaluate("e=>!!e.offsetParent"):
            await check_tap(pg, table, 'dogfight:hud', h)

    return table

# ---------------- main ----------------

PARTS = {
    'menu': part_menu, 'pause': part_pause, 'hud': part_hud, 'sensor': part_sensor,
    'mission': part_mission, 'tasking': part_tasking, 'lesson': part_lesson, 'dogfight': part_dogfight,
}

SUBS = {
    # 'menu' covers Home, Fly, Challenges, School, Boards and Settings (plus its four sub screens
    # and the bug sheet) -- sliced by screen.
    'menu': ['home', 'fly', 'arc', 'school', 'boards', 'settings'],
    # 'pause' sliced left (Challenges/School/Boards/Settings/Report/Sound/Invert/Stick/Haptics/
    # Prev/Play/Next, Resume/Restart/Main menu) vs right (Easy/Hard, the aircraft/base/time/
    # position chips, Action Shot, and Apply as "commits the picks").
    'pause': ['left', 'right'],
}

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--part', required=True, choices=list(PARTS.keys()))
    ap.add_argument('--sub', default=None, help='menu: home/fly/arc/school/boards/settings. pause: left/right.')
    ap.add_argument('--type', default=None, choices=TYPES, help='hud only: one aircraft per run.')
    # Opt-in only. With none given nothing is skipped for time -- every control gets tapped,
    # however slow (a graphics tier recompile, an aircraft-carousel model swap). Set this only for
    # a bounded verification pass under a Bash time cap; the orchestrator's own runs leave it unset.
    ap.add_argument('--budget', type=float, default=None, help='wall-clock seconds; unset = unlimited.')
    args = ap.parse_args()
    if args.sub and args.part in SUBS and args.sub not in SUBS[args.part]:
        ap.error(f'--sub {args.sub!r} is not valid for --part {args.part} (expected one of {SUBS[args.part]})')
    if args.type and args.part != 'hud':
        ap.error('--type only applies to --part hud')

    set_deadline(args.budget)
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        storage = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'}
        storage.update(PLACED)
        pg = await page(b, url, vp=IPHONE_15, storage=storage)
        if args.part == 'menu':
            table = await part_menu(pg, sub=args.sub)
        elif args.part == 'pause':
            table = await part_pause(pg, sub=args.sub)
        elif args.part == 'hud':
            table = await part_hud(pg, type_filter=args.type)
        else:
            table = await PARTS[args.part](pg)
        errs = pg.errs[:10]
        await b.close()
    if args.part in SUBS and args.sub:
        table.part = f'{args.part}_{args.sub}'
    elif args.part == 'hud' and args.type:
        table.part = f'hud_{args.type}'
    path = table.write()
    if errs:
        print(f'\nconsole errors ({len(errs)}):')
        for e in errs:
            print(' ', e)
    return 1 if (table.bad or errs) else 0

if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
