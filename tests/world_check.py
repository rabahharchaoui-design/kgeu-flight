# Item 4.6a: the region framework. iPhone 15 landscape, Hard.
# (a) Arizona unchanged with no kgeuRegion: the KGEU frame numbers, both bases; pickRegion saves the key.
# (b) For Tokyo Haneda, Paris CDG and Rio Santos Dumont (localStorage.kgeuRegion): the world loads,
#     one base, the runway count, every aircraft from every start (runway, ramp, 1 nm and 3 nm final)
#     for 3 s, then a Cessna autoland from the 3 nm final graded on the home runway.
# (c) water and terrain, (d) the scene, (e) traffic, (f) a mission from a world region switches to
#     Arizona, (g) no console errors or failed requests.
# Usage: .venv/bin/python tests/world_check.py [rjtt,lfpg,sbrj]
import asyncio, sys, json, math
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15, Checks, IGNORE

TYPES = ['cessna', 'alpha', 'reaper', 'f16', 'c130', 'mq9b']
STARTS = ['runway', 'ramp', 'final1', 'final']
WANT_RW = {'rjtt': 4, 'lfpg': 4, 'sbrj': 2}
HOME = {'rjtt': '34R', 'lfpg': '26L', 'sbrj': '20L'}
STUB = "window.__kgeuReload=()=>{window.__reloaded=(window.__reloaded||0)+1;};"
BASE = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'}

# one start: 3 s of flight in 1/30 s steps (no render), the state before and after
FLY3 = """([t,pos])=>{const K=window.__kgeu;K.pick(t);K.pickPos(pos);K.start(pos);
  const s0=K.state(),fr=K.wframe(),B=K.BASES[fr.base0],thr=[Math.sin(fr.rh)*fr.thr01,-Math.cos(fr.rh)*fr.thr01];
  const d0=Math.hypot(s0.pos.x-thr[0],s0.pos.z-thr[1]);
  for(let i=0;i<90;i++)K.stepFrame(1/30,false,true);
  const s=K.state(),hdg=((-new THREE.Euler().setFromQuaternion(s.quat,'YXZ').y*180/Math.PI)%360+360)%360;
  return {crashed:s.crashed,why:s.crashReason,g:s.onGround,agl:s.agl,vy:s.vel.y,paved:K.isPaved(s.pos.x,s.pos.z),hdg:hdg,
    rampHdg:B.rampHdg,d0:d0,d1:Math.hypot(s.pos.x-thr[0],s.pos.z-thr[1]),x:s.pos.x,z:s.pos.z};}"""


def adiff(a, b):
    return abs((a - b + 540) % 360 - 180)


async def new_page(b, url, region):
    st = dict(BASE)
    if region != 'az':
        st['kgeuRegion'] = region
    pg = await page(b, url, vp=IPHONE_15, storage=st)
    return pg


async def watch(pg):
    pg.failed = []
    pg.on('requestfailed', lambda r: pg.failed.append(r.url + ' ' + (r.failure or '')) if not any(k in (r.failure or '') for k in IGNORE) else None)
    pg.on('response', lambda r: pg.failed.append(f'{r.status} {r.url}') if r.status >= 400 and 'fonts' not in r.url else None)


async def arizona(c, b, url):
    print('\n--- Arizona ---')
    ctx_pg = await new_page(b, url, 'az')
    pg = ctx_pg
    await pg.context.add_init_script(STUB); await pg.evaluate("()=>{" + STUB + "}")
    r = await pg.evaluate("()=>{const K=window.__kgeu;return {id:K.REGION.id,fr:K.wframe(),bases:Object.keys(K.BASES),rw:K.RUNWAYS.length,ready:K.WORLD.ready}}")
    c('no kgeuRegion: Arizona', r['id'] == 'az' and r['ready'], r['id'])
    f = r['fr']
    c('KGEU frame unchanged', abs(f['rh'] - 26 * math.pi / 180) < 1e-9 and f['len'] == 2179 and f['thr01'] == 213.7
      and abs(f['thr19'] - (2179 - 305.1)) < 1e-9 and f['woff'] == [0, 0] and f['fieldFt'] == 1071 and f['home'] == '1', f)
    c('BASES: kgeu and luke', 'kgeu' in r['bases'] and 'luke' in r['bases'], r['bases'])
    s = await pg.evaluate(FLY3, ['cessna', 'runway'])
    c('Arizona runway start still fine', not s['crashed'] and s['paved'], s)
    await pg.evaluate("()=>window.__kgeu.pickRegion('rjtt')")
    k = await pg.evaluate("()=>({r:localStorage.getItem('kgeuRegion'),res:sessionStorage.getItem('kgeuResume'),rl:window.__reloaded})")
    c('pickRegion(rjtt) from Arizona saves the key and reloads', k['r'] == 'rjtt' and k['rl'] == 1 and json.loads(k['res']) == {'screen': 'fly'}, k)
    c('Arizona: no console errors', not pg.errs, pg.errs[:3])
    await pg.context.close()


async def region(c, b, url, rid, tris):
    print(f'\n--- {rid} ---')
    pg = await new_page(b, url, rid)
    await watch(pg)
    await pg.context.add_init_script(STUB); await pg.evaluate("()=>{" + STUB + "}")
    await pg.wait_for_function("()=>window.__kgeu.WORLD.ready||window.__kgeu.WORLD.err", timeout=20000)
    r = await pg.evaluate("""()=>{const K=window.__kgeu;return {id:K.REGION.id,ready:K.WORLD.ready,err:K.WORLD.err,ms:K.WORLD.ms,
      bases:Object.keys(K.BASES),rw:K.RUNWAYS.length,fr:K.wframe(),WB:K.WB}}""")
    c(f'{rid}: WORLD.ready', r['ready'] and r['id'] == rid, (r['err'], r['ms']))
    c(f'{rid}: one base, the region', r['bases'] == [rid], r['bases'])
    c(f'{rid}: {WANT_RW[rid]} runways', r['rw'] == WANT_RW[rid], r['rw'])
    c(f'{rid}: home runway {HOME[rid]}', r['fr']['home'] == HOME[rid], r['fr'])
    # (b) every aircraft from every start
    bad = []
    for t in TYPES:
        for pos in STARTS:
            s = await pg.evaluate(FLY3, [t, pos])
            why = None
            if s['crashed']: why = 'crashed: ' + s['why']
            elif pos in ('runway', 'ramp'):
                if not s['paved'] or not s['g'] or s['agl'] > 2: why = 'not on pavement'
                elif pos == 'ramp' and adiff(s['hdg'], s['rampHdg']) > 20: why = 'ramp heading'
            else:
                if s['g'] or s['agl'] < (100 if pos == 'final' else 60) or s['vy'] >= 0 or s['d1'] >= s['d0']: why = 'not on final'
            if why: bad.append((t, pos, why, {k: (round(v, 1) if isinstance(v, float) else v) for k, v in s.items()}))
    c(f'{rid}: 6 aircraft x 4 starts fly 3 s', not bad, bad[:4])
    # triangles from the runway, rendered
    await pg.evaluate("()=>{const K=window.__kgeu;K.pick('cessna');K.pickPos('runway');K.start('runway');K.stepFrame(1/30);K.stepFrame(1/30);}")
    tri = await pg.evaluate("()=>window.__kgeu.rinfo()")
    tris[rid] = {'runway': tri, 'airport': sum(v for k, v in r['WB']['tris'].items() if k not in ('city', 'roads', 'roadsPrimary', 'bridges', 'piers')),
                 'city': sum(v for k, v in r['WB']['tris'].items() if k in ('city', 'roads', 'roadsPrimary', 'bridges', 'piers'))}
    c(f'{rid}: airport under 60k triangles, city and roads under 150k', tris[rid]['airport'] < 60000 and tris[rid]['city'] < 150000, tris[rid])
    # autoland from the 3 nm final in a Cessna
    await pg.evaluate("()=>{const K=window.__kgeu;K.pick('cessna');K.pickPos('final');K.start('final');K.auto();}")
    land = None
    for _ in range(48):
        land = await pg.evaluate("""()=>{const K=window.__kgeu;for(let i=0;i<150;i++){K.stepFrame(1/30,false,true);const s=K.state();if(s.onGround||s.crashed)break;}
          const s=K.state(),f=K.runwayFix(s.pos.x,s.pos.z);return {g:s.onGround,crashed:s.crashed,why:s.crashReason,t:s.time,fix:f&&f.num}}""")
        if land['g'] or land['crashed']: break
    await pg.evaluate("()=>{for(let i=0;i<6;i++)window.__kgeu.stepFrame(1/30)}")
    await pg.wait_for_timeout(300)
    badge = await pg.evaluate("()=>document.getElementById('gBadge').classList.contains('on')")
    c(f'{rid}: Cessna autoland touches down on {HOME[rid]} within 4 min', land['g'] and not land['crashed'] and land['fix'] == HOME[rid] and land['t'] < 240, land)
    c(f'{rid}: brief landing card', badge)
    # (c) water and terrain
    # the bay point east of the ARP: 3 km at Haneda; 2 km at Santos Dumont, where the data's water mask
    # meets the Niteroi shore at about 2.6 km
    bay = 2000 if rid == 'sbrj' else 3000
    w = await pg.evaluate("""(bay)=>{const K=window.__kgeu,o=K.wframe().woff,ax=-o[0],az=-o[1];
      let hi=-1e9;for(let i=-5;i<=5;i++)for(let j=-5;j<=5;j++){const x=ax-14142+i*1000,z=az-14142+j*1000;hi=Math.max(hi,K.groundHeight(x,z));}
      return {bay:K.isWater(ax+bay,az),bayH:K.groundHeight(ax+bay,az),arp:K.isWater(ax,az),arpH:K.groundHeight(ax,az),nw:hi}}""", bay)
    if rid in ('rjtt', 'sbrj'):
        c(f'{rid}: water {bay/1000:.0f} km east of the ARP, height 0; land at the ARP', w['bay'] and abs(w['bayH']) < 0.01 and not w['arp'], w)
    else:
        c('lfpg: ARP at about 0, hills over 50 m 20 km north west', abs(w['arpH']) < 3 and w['nw'] > 50 and not w['arp'], w)
    # (d) the scene
    await pg.evaluate("()=>window.__kgeu.setTOD('night')")
    sc = await pg.evaluate("""()=>{const K=window.__kgeu,L=K.AL[K.REGION.icao];return {al:!!L,vis:!!(L&&L.pts.visible),n:K.WB.n}}""")
    c(f'{rid}: AL layer, terminals, city, taxiway lights at night', sc['al'] and sc['vis'] and sc['n'].get('terminals', 0) > 0
      and sc['n'].get('city', 0) > 500 and sc['n'].get('twLights', 0) > 0, sc)
    await pg.evaluate("()=>window.__kgeu.setTOD('day')")
    # (e) traffic after 90 s
    tf = await pg.evaluate("""()=>{const K=window.__kgeu;K.TFC.auto=true;K.pick('cessna');K.pickPos('ramp');K.start('ramp');
      for(let i=0;i<900;i++)K.stepFrame(0.1,false,true);const L=K.tfcList(),A=L.filter(o=>o.type==='airliner');
      return {n:A.length,heli:L.filter(o=>o.type==='heli').length,st:A.map(o=>o.state)}}""")
    c(f'{rid}: 4 to 7 airliners after 90 s, one on final, rollout or taxi', 4 <= tf['n'] <= 7 and any(s in ('final', 'rollout', 'taxi_in', 'taxi_out') for s in tf['st']), tf)
    # (f) a mission from here switches to Arizona
    if rid == 'rjtt':
        await pg.evaluate("()=>{window.__kgeu.pick('c130');window.__kgeu.start('drop');}")
        k = await pg.evaluate("()=>({r:localStorage.getItem('kgeuRegion'),res:sessionStorage.getItem('kgeuResume'),rl:window.__reloaded})")
        res = json.loads(k['res'] or 'null')
        c("start('drop') in Tokyo switches to Arizona with a resume", k['r'] == 'az' and k['rl'] == 1 and res and res['start']['mode'] == 'drop', k)
    c(f'{rid}: no console errors', not pg.errs, pg.errs[:3])
    c(f'{rid}: no failed requests', not pg.failed, pg.failed[:3])
    await pg.context.close()


async def main():
    regs = sys.argv[1].split(',') if len(sys.argv) > 1 else ['rjtt', 'lfpg', 'sbrj']
    c = Checks(); tris = {}
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        await arizona(c, b, url)
        for rid in regs:
            await region(c, b, url, rid, tris)
        await b.close()
    print('\ntriangles', json.dumps(tris))
    sys.exit(c.done('world_check'))

asyncio.run(main())
