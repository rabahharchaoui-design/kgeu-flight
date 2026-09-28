# C-130 missions: the airdrop scores on distance from the DZ centre, the assault
# landing scores on touchdown point and stopping distance.
import asyncio, os, sys, json, threading, functools, http.server, socketserver
from playwright.async_api import async_playwright

# Serve over http rather than file://: the radio clips are fetched at runtime and
# fetch() is blocked on file:// origins, so a file:// run would silently test a
# game with no radio audio.
def serve(root):
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=root)
    class Q(socketserver.TCPServer): allow_reuse_address = True
    srv = Q(('127.0.0.1', 0), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f'http://127.0.0.1:{srv.server_address[1]}/index.html'
THREE=open('node_modules/three/build/three.min.js').read()
SRV,URL=serve(os.path.abspath('.'))
SHOTS=os.path.abspath('overnight-screenshots')
fails=[]
def chk(n,c,d=''):
    print(('  ok   ' if c else '  FAIL ')+n+(('  '+d) if d else ''))
    if not c: fails.append(n)

async def main():
  os.makedirs(SHOTS,exist_ok=True)
  async with async_playwright() as p:
    b=await p.chromium.launch(args=['--use-gl=swiftshader','--enable-unsafe-swiftshader'])
    pg=await (await b.new_context(viewport={'width':844,'height':390},is_mobile=True,has_touch=True,device_scale_factor=2)).new_page()
    errs=[]
    pg.on('pageerror',lambda e:errs.append(str(e)))
    await pg.route('**/three.min.js',lambda r:r.fulfill(body=THREE,content_type='application/javascript'))
    await pg.route('**/fonts.googleapis.com/**',lambda r:r.abort())
    await pg.goto(URL); await pg.wait_for_timeout(2500)
    await pg.wait_for_function("()=>{const s=document.getElementById('splash');return !s||s.classList.contains('gone')}", timeout=30000)

    print('-- airdrop --')
    await pg.evaluate("()=>{window.__kgeu.pick('c130');window.__kgeu.start('drop');}")
    await pg.wait_for_timeout(1200)
    s=await pg.evaluate("()=>{const K=window.__kgeu,s=K.state();return {agl:s.agl,kt:s.ias*1.943844,type:s.type,on:K.MISS.on,kind:K.MISS.kind};}")
    chk('spawns as a C-130 on the drop run', s['type']=='c130' and s['on'] and s['kind']=='drop', json.dumps({k:round(v,1) if isinstance(v,float) else v for k,v in s.items()}))
    chk('spawns inside the drop altitude band', 500 < s['agl']*3.28084 < 1500, f"{s['agl']*3.28084:.0f} ft")

    # fly it onto the DZ: put it a little upwind of centre, still in the window
    res=await pg.evaluate("""()=>{const K=window.__kgeu,s=K.state();
      s.pos.x=K.DROPZ.x+260; s.pos.z=K.DROPZ.z; s.pos.y=s.agl>0?s.pos.y:s.pos.y;
      return [K.MISS.armed, s.agl];}""")
    await pg.wait_for_timeout(700)
    armed=await pg.evaluate("()=>window.__kgeu.MISS.armed")
    chk('drop window arms in the band', armed, str(armed))
    chk('DROP button is offered', await pg.is_visible('#bDrop'),
        str(await pg.evaluate("()=>document.getElementById('bDrop').hidden")))
    await pg.screenshot(path=f'{SHOTS}/mission_drop_run.png')

    await pg.evaluate("()=>window.__kgeu.missDrop()")
    dropped=await pg.evaluate("()=>window.__kgeu.MISS.dropped")
    chk('bundle leaves the aircraft', dropped)
    # run the pallet down without waiting on real time
    await pg.evaluate("()=>window.__kgeu.missTick(4000,1/60)")
    r=await pg.evaluate("()=>window.__kgeu.MISS.result")
    chk('bundle reaches the ground and scores', bool(r), json.dumps(r))
    if r: chk('scored on distance from the DZ centre', 'dist' in r and r['dist']>=0, f"{r['dist']:.0f} m")
    await pg.wait_for_timeout(400)
    chk('result card is up', await pg.is_visible('#missOv'))
    await pg.screenshot(path=f'{SHOTS}/mission_drop_score.png')

    print('-- short field --')
    await pg.evaluate("()=>{window.__kgeu.start('short');}")
    await pg.wait_for_timeout(1200)
    s=await pg.evaluate("""()=>{const K=window.__kgeu,s=K.state();const Z=K.lzUV(s.pos.x,s.pos.z);
      return {u:Z[0],v:Z[1],agl:s.agl,kt:s.ias*1.943844,kind:K.MISS.kind};}""")
    chk('spawns on final to the strip, runway 27', s['kind']=='short' and s['u']>1000 and abs(s['v'])<60,
        f"u {s['u']:.0f} v {s['v']:.0f} agl {s['agl']:.0f} m")
    chk('final approach is over flat desert, not the White Tanks', abs(s['agl']-240)<12, f"{s['agl']:.0f} m AGL")
    await pg.screenshot(path=f'{SHOTS}/mission_short_final.png')

    # a touchdown 400 ft in, rolling to a stop 1,600 ft later
    r=await pg.evaluate("""()=>{const K=window.__kgeu,s=K.state();
      // landing on 27: rolling toward -u, touching down 400 ft in from the east end
      s.vel.set(-60,0,0);
      const td=K.lzX(K.LZ.len/2-122,0), tdz=K.lzZ(K.LZ.len/2-122,0);
      K.missTouchdown({type:'touchdown',fpm:420,paved:true,x:td,z:tdz});
      const t=K.MISS.td;
      // park it 488 m (1,600 ft) further down the strip, stopped
      s.pos.x=K.lzX(K.LZ.len/2-122-488,0); s.pos.z=K.lzZ(K.LZ.len/2-122-488,0);
      s.vel.set(0,0,0);
      K.missTick(200,1/60);
      return {td:t,result:K.MISS.result};}""")
    chk('touchdown point measured from the threshold', r['td'] and abs(r['td']['ft']-400)<15, json.dumps(r['td']))
    chk('stopping distance measured and scored', bool(r['result']), json.dumps(r['result']))
    if r['result']: chk('stop distance about 1,600 ft', abs(r['result']['stopFt']-1600)<40, str(r['result']['stopFt']))
    await pg.wait_for_timeout(400)
    await pg.screenshot(path=f'{SHOTS}/mission_short_score.png')

    chk('no console errors', not errs, ' | '.join(errs[:2]))
    await b.close()
  print(f'FAILS {len(fails)}'+((': '+'; '.join(fails)) if fails else ''))
  sys.exit(1 if fails else 0)
asyncio.run(main())
