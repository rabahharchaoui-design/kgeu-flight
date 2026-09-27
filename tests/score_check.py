# Scoring: landing grades, per aircraft records, the pilot log, achievements,
# the NEW RECORD banner, and the reset.
import asyncio, os, sys, json, threading, functools, http.server, socketserver
from playwright.async_api import async_playwright

def serve(root):
    h=functools.partial(http.server.SimpleHTTPRequestHandler,directory=root)
    class Q(socketserver.TCPServer): allow_reuse_address=True
    srv=Q(('127.0.0.1',0),h)
    threading.Thread(target=srv.serve_forever,daemon=True).start()
    return srv,f'http://127.0.0.1:{srv.server_address[1]}/index.html'

THREE=open('node_modules/three/build/three.min.js').read()
SRV,URL=serve(os.path.abspath('.'))
SHOTS=os.path.abspath('overnight-screenshots')
fails=[]
def chk(n,c,d=''):
    print(('  ok   ' if c else '  FAIL ')+n+(('  '+d) if d else ''))
    if not c: fails.append(n)

# a touchdown event as the physics would emit it
TD = """(o)=>{const K=window.__kgeu,s=K.state();
  const u=o.u, v=o.v;
  const e={type:'touchdown',fpm:o.fpm,paved:true,
           x:K.wX(u,v),z:K.wZ(u,v),ias:o.kt/1.943844,bank:0,wdir:o.wdir||10,wkt:o.wkt||3};
  s.pos.x=e.x;s.pos.z=e.z;
  return K.gradeLanding(e);}"""

async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(args=['--use-gl=swiftshader','--enable-unsafe-swiftshader'])
    pg=await (await b.new_context(viewport={'width':844,'height':390},is_mobile=True,has_touch=True,device_scale_factor=2)).new_page()
    errs=[]
    pg.on('pageerror',lambda e:errs.append(str(e)))
    await pg.route('**/three.min.js',lambda r:r.fulfill(body=THREE,content_type='application/javascript'))
    await pg.route('**/fonts.googleapis.com/**',lambda r:r.abort())
    await pg.goto(URL); await pg.wait_for_timeout(2200)
    await pg.evaluate("()=>{window.__kgeu.scReset();window.__kgeu.pick('cessna');window.__kgeu.start('runway');}")
    await pg.wait_for_timeout(1200)

    AIM = 213.7+300      # 1,000 ft in from the runway 1 threshold
    print('-- grading --')
    g=await pg.evaluate(TD,{'u':AIM,'v':0,'fpm':60,'kt':65})
    chk('a greaser on the aim point grades A', g and g['letter']=='A', json.dumps({'pts':g['pts'],'l':g['letter']}) if g else 'none')
    g2=await pg.evaluate(TD,{'u':AIM+500,'v':11,'fpm':420,'kt':85})
    chk('fast, long, off centreline and firm grades poorly', g2['letter'] in 'DF', f"{g2['letter']} {g2['pts']} pts")
    chk('the card breaks the grade into four parts', len(g2['parts'])==4, json.dumps([p[0] for p in g2['parts']]))
    g3=await pg.evaluate(TD,{'u':AIM+120,'v':3,'fpm':170,'kt':70})
    chk('a workmanlike landing lands mid scale', g3['letter'] in 'BC', f"{g3['letter']} {g3['pts']} pts")
    chk('sink rate dominates the score', g['parts'][0][2] > g2['parts'][0][2], f"{g['parts'][0][2]} vs {g2['parts'][0][2]}")

    # each input moves its own component and the total
    worse=await pg.evaluate(TD,{'u':AIM,'v':0,'fpm':600,'kt':65})
    chk('a hard touchdown alone drops the grade', worse['pts']<g['pts']-20, f"{worse['pts']} vs {g['pts']}")
    off=await pg.evaluate(TD,{'u':AIM,'v':14,'fpm':60,'kt':65})
    chk('drifting off the centreline alone drops it', off['pts']<g['pts']-10, f"{off['pts']} vs {g['pts']}")

    print('-- runways --')
    r=await pg.evaluate("""()=>{const K=window.__kgeu,out={};
      out.kgeu=K.runwayFix(K.wX(500,2),K.wZ(500,2));
      const lu=(u,v)=>[K.LUKE.x+Math.sin(K.LUKE.h)*u+Math.cos(K.LUKE.h)*v,
                       K.LUKE.z-Math.cos(K.LUKE.h)*u+Math.sin(K.LUKE.h)*v];
      const a=lu(-1200,-152.5); out.luke=K.runwayFix(a[0],a[1]);
      out.lz=K.runwayFix(K.lzX(-300,1),K.lzZ(-300,1));
      out.desert=K.runwayFix(-20000,20000);
      return out;}""")
    chk('a Glendale touchdown is graded against runway 1', r['kgeu'] and 'Glendale' in r['kgeu']['name'], json.dumps(r['kgeu']))
    chk('a Luke touchdown is graded against 03L', r['luke'] and '03L' in r['luke']['name'], json.dumps(r['luke']))
    chk('an assault strip touchdown is graded against the strip', r['lz'] and 'assault' in r['lz']['name'], json.dumps(r['lz']))
    chk('a landing in the desert is not graded', r['desert'] is None)

    print('-- records, log and achievements --')
    await pg.evaluate("()=>{const K=window.__kgeu;K.scRecord('cessna',{pts:70,letter:'C',fpm:300,off:5});}")
    b1=await pg.evaluate("()=>window.__kgeu.scRecord('cessna',{pts:91,letter:'A',fpm:80,off:1})")
    b2=await pg.evaluate("()=>window.__kgeu.scRecord('cessna',{pts:60,letter:'D',fpm:500,off:9})")
    chk('a better landing sets a new record', b1 is True)
    chk('a worse landing does not', b2 is False)
    chk('the F-16 record ranks on time, not points', await pg.evaluate(
        "()=>{const K=window.__kgeu;K.scRecord('f16',{secs:200,g:5});return K.scRecord('f16',{secs:150,g:7});}") is True)
    chk('a slower dash does not beat it', await pg.evaluate(
        "()=>window.__kgeu.scRecord('f16',{secs:400,g:9})") is False)

    log=await pg.evaluate("""()=>{const K=window.__kgeu;
      K.logLanding({letter:'A'});K.logLanding({letter:'B'});K.logLanding({letter:'A'});
      K.logLanding({letter:'F'});K.logLanding({letter:'B'});
      return JSON.parse(JSON.stringify(K.SCORE.log));}""")
    chk('the log counts landings', log['landings']==5, json.dumps(log))
    chk('best streak of B or better is 3', log['bestStreak']==3, json.dumps(log))
    chk('an F breaks the streak', log['streak']==1, json.dumps(log))

    a=await pg.evaluate("()=>{const K=window.__kgeu;K.achGrant('greaser');return Object.keys(K.SCORE.ach);}")
    chk('an achievement is granted once', a==['greaser'], json.dumps(a))
    again=await pg.evaluate("()=>window.__kgeu.achGrant('greaser')")
    chk('granting it twice is a no-op', again is False)
    chk('the banner shows', await pg.evaluate("()=>document.getElementById('banner').classList.contains('on')"))
    await pg.screenshot(path=f'{SHOTS}/score_banner.png')

    print('-- persistence --')
    saved=await pg.evaluate("()=>localStorage.getItem('kgeuScores')")
    chk('everything is saved to localStorage', saved and 'greaser' in saved and 'bestStreak' in saved, str(len(saved or ''))+' bytes')
    await pg.reload(); await pg.wait_for_timeout(2200)
    back=await pg.evaluate("()=>{const K=window.__kgeu;return {l:K.SCORE.log.landings,a:Object.keys(K.SCORE.ach),b:!!K.SCORE.best.cessna};}")
    chk('records survive a reload', back['l']==5 and back['a']==['greaser'] and back['b'], json.dumps(back))

    print('-- records screen --')
    await pg.evaluate("()=>window.__kgeu.recOpen()")
    await pg.wait_for_timeout(500)
    chk('records screen opens', await pg.is_visible('#recOv'))
    # section headers are text-transform:uppercase, and inner_text returns rendered text
    body=(await pg.inner_text('#recBody')).lower()
    for want in ['pilot log','landings','best streak','cessna 172','f-16c viper',
                 'c-130h hercules','achievements','first greaser','luke to glendale',
                 'airdrop','short field','loiter and strike']:
        chk(f'records screen shows {want!r}', want in body)
    await pg.screenshot(path=f'{SHOTS}/score_records.png')

    print('-- reset needs two taps --')
    await pg.click('#recReset'); await pg.wait_for_timeout(200)
    mid=await pg.evaluate("()=>window.__kgeu.SCORE.log.landings")
    chk('one tap does not erase', mid==5, str(mid))
    await pg.click('#recReset'); await pg.wait_for_timeout(300)
    after=await pg.evaluate("()=>{const K=window.__kgeu;return {l:K.SCORE.log.landings,a:Object.keys(K.SCORE.ach),b:Object.keys(K.SCORE.best)};}")
    chk('the second tap erases everything', after['l']==0 and not after['a'] and not after['b'], json.dumps(after))

    chk('no console errors', not errs, ' | '.join(errs[:2]))
    await b.close()
  print(f'FAILS {len(fails)}'+((': '+'; '.join(fails)) if fails else ''))
  sys.exit(1 if fails else 0)
asyncio.run(main())
