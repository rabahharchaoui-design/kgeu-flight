# Callsign check (3.8): the radio callsign must match the selected aircraft at every spawn.
# Sweep: every type x {kgeu, luke} x {runway, ramp, final} x {rookie, pilot}, started the way
# the pause menu Change flight panel does it (pick, pickBase, pickPos, start), ~45 simulated
# seconds each, every radio line that played captured with window.__kgeu.radioLog().
#  (a) the player's own lines (kind pilot/uav, or who === AC.cs) carry AC.cs or AC.csS and
#      use only this type's callsign clip
#  (b) tower/ground/approach/range lines that address an aircraft address AC.cs or AC.csS,
#      except the ambient chatter set (Viper 21 flight and friends), printed as other traffic
#  (c) no line outside the ambient set carries another type's callsign text or clip
#  (d) switch aircraft twice in a row mid-exchange through the pause path and re-check
#  (e) the player's own first call is the first thing heard, ambient never plays ahead of it
# Run: .venv/bin/python tests/callsign_check.py
import asyncio, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, IPHONE_15
ok = Checks()
K = 'window.__kgeu'
BROADCAST = ('Attention all aircraft', 'Crash, crash, crash')

def audit(r, tag, types, other):
    """r: {cs,csS,id,log}. Returns a list of mismatch strings."""
    bad = []
    cs, csS, me = r['cs'], r['csS'], r['id']
    CSC, CSCS = types['CSC'], types['CSCS']
    mine = {CSC[me], CSCS[me]}
    foreign_clips = {c for t in CSC for c in (CSC[t], CSCS[t]) if t != me} - mine
    foreign_txt = [s for t, v in types['cs'].items() if t != me for s in v if s not in (cs, csS)]
    for l in r['log']:
        txt, clips = l['text'], l['clips'] if isinstance(l['clips'], list) else []
        ids = [c[2:] for c in clips if c[:2] in ('t_', 'p_')]
        line = f"{tag}  [{l['t']:5.1f}s] {l['who']}: {txt}  {clips}"
        if l['amb']:
            other.append(line)
            continue
        if l['who'] == 'Instructor':
            continue
        if l['type'] != me:
            bad.append('stale AC ' + l['type'] + '  ' + line)
        hascs = cs in txt or csS in txt
        if l['kind'] in ('pilot', 'uav') or l['who'] == cs:
            if not hascs:
                bad.append('(a) own line without callsign  ' + line)
        elif l['kind'] == 'tower' and not txt.startswith(BROADCAST) and not hascs:
            bad.append('(b) controller line not addressed to us  ' + line)
        for s in foreign_txt:
            if s in txt:
                bad.append(f'(c) other type callsign "{s}"  ' + line)
        for c in ids:
            if c in foreign_clips:
                bad.append(f'(c) other type clip {c}  ' + line)
    return bad

def order(r, tag):
    """(e): nothing ambient before our first call, and nothing ambient between a call to us and our readback."""
    bad, log = [], [l for l in r['log'] if l['who'] != 'Instructor']
    if not log:
        return bad
    if log[0]['amb']:
        bad.append(f"(e) ambient heard before our first call  {tag}  {log[0]['who']}: {log[0]['text']}")
    pend = False
    for l in log:
        if l['amb'] and pend:
            bad.append(f"(e) ambient during our exchange  {tag}  {l['who']}: {l['text']}")
        if not l['amb'] and l['kind'] == 'tower' and (r['cs'] in l['text'] or r['csS'] in l['text']) and 'cleared' in l['text']:
            pend = True
        if l['kind'] == 'pilot':
            pend = False
    return bad

RUN = """async([t,base,pos,skill,secs])=>{const K=window.__kgeu;
  K.setSkill(skill);
  // the pause menu path: Change flight picks, then Apply
  if(K.state()&&K.state().time>0&&!K.state().crashed){K.togglePause();}
  K.pick(t);K.pickBase(base);K.pickPos(pos);K.radioLog(true);K.start(pos);
  const n=Math.round(secs*30);for(let i=0;i<n;i++)K.stepFrame(1/30,false,true);
  const s=K.state();
  return {id:K.TYPES[t].id,cs:K.TYPES[t].cs,csS:K.TYPES[t].csS,log:K.radioLog(true),
          q:K.radioQ().map(l=>({who:l.who,kind:l.kind,text:l.text,clips:l.clips,amb:K.CHAT.some(p=>p.indexOf(l)>=0),t:-1,type:t})),
          base:s.base,type:s.type};}"""

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
        await pg.evaluate(f"()=>{K}.initAudio()")
        types = await pg.evaluate("""()=>{const T=window.__kgeu.TYPES,o={cs:{}};for(const k in T)o.cs[k]=[T[k].cs,T[k].csS];
            o.CSC={cessna:'cs_skyhawk',alpha:'cs_pipistrel',reaper:'cs_reaper',f16:'cs_viper',c130:'cs_herky',mq9b:'cs_skyguardian',archer:'cs_archer',a10:'cs_hawg',b737:'cs_pocket737',a320:'cs_pocket320',b747:'cs_pocket747'};
            o.CSCS={cessna:'cs_skyhawk_s',alpha:'cs_pipistrel_s',reaper:'cs_reaper_s',f16:'cs_viper',c130:'cs_herky',mq9b:'cs_skyguardian_s',archer:'cs_archer_s',a10:'cs_hawg',b737:'cs_pocket737',a320:'cs_pocket320',b747:'cs_pocket747'};return o;}""")
        # the clip tables in the page must be the ones this test assumes
        same = await pg.evaluate("""(o)=>{const T=window.__kgeu.TYPES;return Object.keys(T).every(k=>o.CSC[k]&&o.CSCS[k]);}""", types)
        ok('clip table covers every type', same)
        bad, other, heard = [], [], 0
        for skill in ('pilot', 'rookie'):
            for t in types['cs']:
                for base in ('kgeu', 'luke'):
                    for pos in ('runway', 'ramp', 'final'):
                        r = await pg.evaluate(RUN, [t, base, pos, skill, 45])
                        tag = f'{t}/{base}/{pos}/{skill}'
                        r['log'] += r['q']
                        heard += len(r['log'])
                        # an airliner picked at a short base flies from its home, Sky Harbor (planes2's long runway rule)
                        want_base = base if await pg.evaluate(f"()=>{K}.baseOK('{t}','{base}')") else 'phx'
                        if r['type'] != t or r['base'] != want_base:
                            bad.append(f'{tag}  state is {r["type"]}/{r["base"]}')
                        own = [l for l in r['log'] if not l['amb'] and (r['cs'] in l['text'] or r['csS'] in l['text'])]
                        if not own:
                            bad.append(f'{tag}  no call to or from us in 45 s')
                        bad += audit(r, tag, types, other) + order(r, tag)
        ok(f'sweep: 72 flights, {heard} lines, every callsign matches', not bad, f'{len(bad)} mismatches')
        # (d): switch aircraft mid-exchange, twice in a row, through the pause menu path
        dbad = []
        for seq in (('f16', 'mq9b', 'reaper'), ('reaper', 'f16', 'mq9b'), ('mq9b', 'c130', 'cessna')):
            await pg.evaluate(RUN, [seq[0], 'luke', 'runway', 'pilot', 1.2])   # tower has called, readback pending
            r1 = await pg.evaluate(RUN, [seq[1], 'luke', 'runway', 'pilot', 1.2])
            r2 = await pg.evaluate(RUN, [seq[2], 'luke', 'runway', 'pilot', 45])
            for r, tt in ((r1, seq[1]), (r2, seq[2])):
                r['log'] += r['q']
                dbad += audit(r, 'switch ' + '>'.join(seq) + ' now ' + tt, types, other) + order(r, 'switch ' + tt)
        ok('pause menu switch twice mid-exchange: callsign follows', not dbad, f'{len(dbad)} mismatches')
        bad += dbad
        # the pattern clearance and the nice landing call come from the home base's tower
        for base, twr, rwy, gnd in (('kgeu', 'Glendale Tower 121.0', 'runway 1,', 'ground 118.0'), ('luke', 'Luke Tower 133.45', 'runway 03L,', 'ground 121.8')):
            r = await pg.evaluate("""([base])=>{const K=window.__kgeu,B=K.BASES[base];K.pick('cessna');K.pickBase(base);K.pickPos('runway');K.start('runway');
              for(let i=0;i<60;i++)K.stepFrame(1/30,false,true);
              const s=K.state(),lk=base==='luke',h=B.hdg*Math.PI/180,put=(u,y)=>{               // u along the extended centreline from the threshold
                const x=lk?K.BASES.luke.fin(-u-300)[0]:K.BASES.kgeu.fin(-u-300)[0],z=lk?K.BASES.luke.fin(-u-300)[1]:K.BASES.kgeu.fin(-u-300)[1];
                s.pos.set(x,y,z);s.quat.setFromEuler(new THREE.Euler(0,-h,0,'YXZ'));s.onGround=false;};
              K.radioLog(true);put(-3000,s.pos.y+300);s.agl=300;K.atcUpdate();put(-2500,s.pos.y);s.agl=200;K.atcUpdate();
              const p=s.pos,e={x:0,z:0};put(200,p.y);e.x=s.pos.x;e.z=s.pos.z;K.atcTouchdown(e);
              return K.radioLog(true).map(l=>l.who+': '+l.text);}""", [base])
            land = [l for l in r if 'check wheels down' in l]
            nice = [l for l in r if 'nice landing' in l]
            ok(f'{base}: pattern clearance from {twr}, {rwy.rstrip(",")}', land and land[0].startswith(twr) and rwy in land[0], land or r)
            ok(f'{base}: nice landing from {twr}, contact {gnd}', nice and nice[0].startswith(twr) and gnd in nice[0], nice or r)
        for l in bad:
            print('  MISMATCH ' + l)
        seen = sorted({o.split('] ', 1)[1] for o in other})
        print(f'\n  other traffic heard ({len(other)} times, {len(seen)} distinct lines):')
        for o in seen:
            print('    ' + o)
        await pg.evaluate(f"()=>{K}.stepFrame(0,true)")
        ok('no page errors', not pg.errs, pg.errs[:3])
        await b.close()
    srv.shutdown()
    return ok.done('callsign_check')

sys.exit(asyncio.run(main()))
