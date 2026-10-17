# Runways item 7 "before" audit: every flyable aircraft model measured at true scale against its
# real manufacturer / FAA type certificate dimensions. Model for picking/starting a flight and
# reading window.__kgeu.plane(): tests/model_shots.py (plane().g is the model's THREE.Group).
#
# For each type: K.pick(id); K.pickBase(base) (airliners -> 'phx' for a long runway, else 'kgeu');
# K.start('runway'); wait 400 ms; then the world bounding box of plane().g, measured in the
# group's OWN local frame (its position and quaternion are zeroed and matrixWorld refreshed, then
# restored after) so a start heading never skews span/length. Excluded while traversing: THREE.Points
# (light points), and any mesh whose name or an ancestor's name contains 'shadow', 'flame', 'ab' or
# 'pool' or 'lights' (afterburner/exhaust flame, ground light pool, aircraft light points), plus any
# mesh with a CircleGeometry (propeller/fan discs and blur, the same test window.__kgeu.propDiscs
# at index.html:24375 uses to find them).
#
# Assertions: span (x) and length (z) within 3% of the table; height (y) printed, within 8% informational
# only (never fails the run). The AI airliner model (window.__kgeu.TFC.pool.airliner[0].g, reachable
# without flying one) checked against the 737 row with a 5% tolerance. One world check: a 737's main
# gear track (5.7 m) fits a Sky Harbor taxiway (23 m or more) -- no hook exposes Sky Harbor's taxiway
# width (SH_TWY is a local const, not on window.__kgeu, and window.__kgeu.aptEnv does not exist), so
# this prints 'skipped' and does not fail, as instructed.
#
# Usage: .venv/bin/python tests/scale_check.py
import asyncio, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15, Checks

c = Checks()

# real dimensions, metres: span, length, height (manufacturer / FAA type certificate data)
TABLE = {
    'cessna': (11.00, 8.28, 2.72),
    'archer': (10.67, 7.32, 2.22),
    'alpha': (10.50, 6.50, 2.05),
    'reaper': (20.12, 11.00, 3.81),     # MQ-9A
    'mq9b': (24.00, 11.70, 3.81),       # MQ-9B SkyGuardian
    'c130': (40.41, 29.79, 11.66),      # C-130H
    'f16': (9.96, 15.06, 4.88),         # F-16C, wingtip missile rails included
    'a10': (17.53, 16.26, 4.47),
    'b737': (35.79, 39.47, 12.55),      # 737-800 with winglets
    'a320': (35.80, 37.57, 11.76),      # sharklets
    'b747': (64.44, 70.66, 19.41),      # 747-400
}
AIRLINERS = {'b737', 'a320', 'b747'}
SPAN_LEN_TOL = 0.03
HEIGHT_TOL = 0.08
AI_TOL = 0.05

MEASURE_JS = """(sel)=>{
  const K=window.__kgeu;
  const g = sel==='poolAirliner' ? ((K.TFC.pool.airliner||[])[0]||{}).g : (K.plane()||{}).g;
  if(!g) return null;
  const savedPos=g.position.clone(), savedQuat=g.quaternion.clone(), savedScale=g.scale.clone();
  g.position.set(0,0,0); g.quaternion.identity(); g.scale.set(1,1,1);
  g.updateMatrixWorld(true);
  function excluded(o){
    let n=o;
    while(n && n!==g){
      if(n.isPoints) return true;
      const nm=n.name||'';
      if(nm.indexOf('shadow')>=0||nm.indexOf('flame')>=0||nm.indexOf('ab')>=0||nm.indexOf('pool')>=0||nm.indexOf('lights')>=0) return true;
      n=n.parent;
    }
    return false;
  }
  const box=new THREE.Box3(); let any=false;
  g.traverse(o=>{
    if(!o.isMesh||!o.visible||!o.geometry) return;
    if(excluded(o)) return;
    if(o.geometry.type==='CircleGeometry') return;
    if(!o.geometry.boundingBox) o.geometry.computeBoundingBox();
    const bb=o.geometry.boundingBox; if(!bb) return;
    box.union(new THREE.Box3().copy(bb).applyMatrix4(o.matrixWorld)); any=true;
  });
  g.position.copy(savedPos); g.quaternion.copy(savedQuat); g.scale.copy(savedScale);
  g.updateMatrixWorld(true);
  if(!any) return null;
  const size=box.getSize(new THREE.Vector3());
  return {x:size.x, y:size.y, z:size.z};
}"""

ROWS = []   # (type, span_game, span_real, span_pct, len_game, len_real, len_pct, h_game, h_real, h_pct)


def pct(game, real):
    return (game - real) / real * 100


async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})

        for t, (span, length, height) in TABLE.items():
            base = 'phx' if t in AIRLINERS else 'kgeu'
            await pg.evaluate("([t,b])=>{const K=window.__kgeu;K.pick(t);K.pickBase(b);K.start('runway');}", [t, base])
            await pg.wait_for_timeout(400)
            m = await pg.evaluate(MEASURE_JS, 'player')
            if m is None:
                c(f'{t}: measured a bounding box', False, 'plane().g gave nothing to measure')
                continue
            # the model's local frame may have x as span or length depending on build convention;
            # match each axis to whichever of span/length it is closer to, rather than assume x/z
            sx, sz, sy = m['x'], m['z'], m['y']
            if abs(sx - length) + abs(sz - span) < abs(sx - span) + abs(sz - length):
                sx, sz = sz, sx   # x read as length, z as span: swap so sx=span, sz=length below
            span_pct, len_pct, h_pct = pct(sx, span), pct(sz, length), pct(sy, height)
            ROWS.append((t, sx, span, span_pct, sz, length, len_pct, sy, height, h_pct))
            c(f'{t}: span {sx:.2f} m within 3% of {span:.2f} m', abs(span_pct) <= SPAN_LEN_TOL * 100, f'{span_pct:+.1f}%')
            c(f'{t}: length {sz:.2f} m within 3% of {length:.2f} m', abs(len_pct) <= SPAN_LEN_TOL * 100, f'{len_pct:+.1f}%')
            if abs(h_pct) > HEIGHT_TOL * 100:
                print(f'  info  {t}: height {sy:.2f} m vs {height:.2f} m real ({h_pct:+.1f}%, informational, not failing)')

        # the AI airliner model, against the 737 row
        has_pool = await pg.evaluate("()=>!!(window.__kgeu.TFC&&window.__kgeu.TFC.pool&&window.__kgeu.TFC.pool.airliner&&window.__kgeu.TFC.pool.airliner[0])")
        if has_pool:
            m = await pg.evaluate(MEASURE_JS, 'poolAirliner')
            if m is None:
                c('AI airliner (TFC.pool.airliner[0]): measured a bounding box', False, 'nothing to measure')
            else:
                span, length, height = TABLE['b737']
                sx, sz, sy = m['x'], m['z'], m['y']
                if abs(sx - length) + abs(sz - span) < abs(sx - span) + abs(sz - length):
                    sx, sz = sz, sx
                span_pct, len_pct = pct(sx, span), pct(sz, length)
                c(f'AI airliner: span {sx:.2f} m within 5% of 737 {span:.2f} m', abs(span_pct) <= AI_TOL * 100, f'{span_pct:+.1f}%')
                c(f'AI airliner: length {sz:.2f} m within 5% of 737 {length:.2f} m', abs(len_pct) <= AI_TOL * 100, f'{len_pct:+.1f}%')
        else:
            print('  [AI airliner] TFC.pool.airliner[0] not reachable: skipping, not failing')

        # world check: a 737's main gear track (5.7 m) fits a Sky Harbor taxiway (>= 23 m)
        twy = await pg.evaluate("""()=>{const K=window.__kgeu;
          if(typeof K.aptEnv==='function')return {via:'aptEnv',v:K.aptEnv()};
          if(K.TERR&&K.TERR.tw&&K.TERR.tw.length)return {via:'TERR.tw',v:K.TERR.tw.length};
          return null;}""")
        if twy is None:
            print("  [taxiway width] no hook exposes Sky Harbor's taxiway width (aptEnv missing, SH_TWY is a private const): skipped, not failing")
        else:
            print(f'  [taxiway width] found via {twy["via"]}: {twy["v"]!r} (not a width value, needs a real hook; not failing)')

        c('no console errors', not pg.errs, pg.errs[:5])
        await b.close()
    srv.shutdown()

    print('\n%-8s %7s %7s %7s %6s %7s %7s %7s %6s' % ('type', 'span_g', 'span_r', 'span%', 'len_g', 'len_r', 'len%', 'h_g', 'h_r'))
    for t, sg, sr, spct, lg, lr, lpct, hg, hr, hpct in ROWS:
        print('%-8s %7.2f %7.2f %+6.1f%% %7.2f %7.2f %+6.1f%% %7.2f %6.2f (h %+.1f%%)' %
              (t, sg, sr, spct, lg, lr, lpct, hg, hr, hpct))
    sys.exit(c.done('scale_check'))


asyncio.run(main())
