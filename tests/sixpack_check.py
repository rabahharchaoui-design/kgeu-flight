# Six pack: every needle must point at the value it is showing. Read the drawn
# pixels rather than trusting the drawing code, because a needle that is 180
# degrees out still looks like a working instrument in a screenshot.
import asyncio, os, sys, math, json, threading, functools, http.server, socketserver
from playwright.async_api import async_playwright
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
def serve(root):
    h=functools.partial(Quiet,directory=root)
    class Q(socketserver.TCPServer): allow_reuse_address=True
    srv=Q(('127.0.0.1',0),h); threading.Thread(target=srv.serve_forever,daemon=True).start()
    return f'http://127.0.0.1:{srv.server_address[1]}/index.html'
THREE=open('node_modules/three/build/three.min.js').read()
URL=serve(os.path.abspath('.'))
SHOTS=os.path.abspath('overnight-screenshots')
fails=[]
def chk(n,c,d=''):
    print(('  ok   ' if c else '  FAIL ')+n+(('  '+d) if d else ''))
    if not c: fails.append(n)

# Sample a ring inside a gauge and return the canvas angle of the brightest run,
# which is the white needle. Angles are canvas convention: 0 right, +y down.
PROBE = """(o)=>{
  const K=window.__kgeu, C=K.SP_CELL, cv=document.getElementById('sixpack');
  const s=K.state();
  if(o.kt!==undefined) s.ias=o.kt/1.943844;
  if(o.vs!==undefined) s.vel.y=o.vs/196.85;
  if(o.ft!==undefined) s.pos.y=(o.ft-1071)/3.28084+1.5;
  if(o.hdg!==undefined) s.quat.setFromEuler(new THREE.Euler(0,-(o.hdg+12)*Math.PI/180,0,'YXZ'));
  K.drawSixPack();
  const g=cv.getContext('2d'), d=cv.width/(C*3);
  const cx=(o.col*C+C/2)*d, cy=(o.row*C+C/2)*d, r=o.r*d;
  const N=360, ring=new Array(N);
  let best=-1,bestA=0;
  for(let i=0;i<N;i++){
    const a=i/N*2*Math.PI;
    const px=Math.round(cx+Math.cos(a)*r), py=Math.round(cy+Math.sin(a)*r);
    const p=g.getImageData(px,py,1,1).data;
    // 'yellow' isolates the 100 ft altimeter needle, which is #ffc400 against a
    // face of neutral grey ticks and numerals that swamp it on plain luminance.
    const lum=o.metric==='yellow' ? Math.max(0,p[0]-p[2])*(p[3]/255)
                                  : (p[0]+p[1]+p[2])/3*(p[3]/255);
    ring[i]=lum;
    if(lum>best){best=lum;bestA=a;}
  }
  return {ang:bestA*180/Math.PI, lum:best, ring:ring};
}"""

def moved_to(a, b):
    """Where a needle moved TO, in degrees. Signed difference cancels the ticks
    and numerals, which do not move, and leaves a positive peak at the needle's
    new position. More reliable than brightest-pixel on a busy altimeter face."""
    return max(range(len(a)), key=lambda i: b[i]-a[i])

def best_shift(a, b):
    """Circular shift, in degrees, that best aligns ring b onto ring a. The
    heading card rotates rigidly, so correlating the whole ring is far more
    stable than picking the single brightest pixel out of 72 identical ticks."""
    n=len(a)
    ma=sum(a)/n; mb=sum(b)/n
    A=[v-ma for v in a]; B=[v-mb for v in b]
    bestk, bestv = 0, -1e18
    for k in range(n):
        v=sum(A[i]*B[(i+k)%n] for i in range(n))
        if v>bestv: bestv, bestk = v, k
    return bestk

def norm(a): return (a+360)%360
def close(a,b,tol): 
    d=abs(norm(a)-norm(b)); d=min(d,360-d); return d<=tol

async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(args=['--use-gl=swiftshader','--enable-unsafe-swiftshader'])
    pg=await (await b.new_context(viewport={'width':844,'height':390},is_mobile=True,has_touch=True)).new_page()
    await pg.add_init_script("localStorage.setItem('kgeuOnboard','pilot');localStorage.setItem('kgeuTut','1')")  # past the first launch screen; the six pack is a Pilot feature
    errs=[]
    pg.on('pageerror',lambda e:errs.append(str(e)))
    await pg.route('**/three.min.js',lambda r:r.fulfill(body=THREE,content_type='application/javascript'))
    await pg.route('**/fonts.googleapis.com/**',lambda r:r.abort())
    await pg.goto(URL); await pg.wait_for_timeout(2200)
    await pg.wait_for_function("()=>{const s=document.getElementById('splash');return !s||s.classList.contains('gone')}", timeout=30000)
    await pg.evaluate("()=>{window.__kgeu.setTOD('day');window.__kgeu.pick('cessna');window.__kgeu.start('final');}")
    await pg.wait_for_timeout(900)
    await pg.evaluate("()=>window.__kgeu.cycleCam()")        # chase -> cockpit
    await pg.wait_for_timeout(600)
    # pause only to freeze the frame; close the pause sheet, which hides the flight UI
    await pg.evaluate("()=>{window.__kgeu.togglePause();document.getElementById('pauseOv').classList.remove('on')}")
    await pg.wait_for_timeout(300)
    chk('the panel shows in the cockpit view', await pg.is_visible('#sixpack'))

    # --- airspeed: the needle sweeps clockwise from slow to fast ---
    lo=await pg.evaluate(PROBE,{'col':0,'row':0,'r':22,'kt':50})
    hi=await pg.evaluate(PROBE,{'col':0,'row':0,'r':22,'kt':140})
    sweep=norm(hi['ang']-lo['ang'])
    chk('airspeed needle moves with speed', not close(lo['ang'],hi['ang'],8),
        f"50 kt {lo['ang']:.0f} deg, 140 kt {hi['ang']:.0f} deg")
    chk('airspeed needle sweeps clockwise, not backwards', 10 < sweep < 200, f'{sweep:.0f} deg of sweep')
    # 50 kt is near the bottom of the scale, so the needle lives in the lower left
    chk('50 kt sits in the lower left of the dial', 90 < norm(lo['ang']) < 200, f"{lo['ang']:.0f} deg")

    # --- vertical speed: zero points at 9 o'clock, climb goes up ---
    z =await pg.evaluate(PROBE,{'col':2,'row':1,'r':22,'vs':0})
    up=await pg.evaluate(PROBE,{'col':2,'row':1,'r':22,'vs':1500})
    dn=await pg.evaluate(PROBE,{'col':2,'row':1,'r':22,'vs':-1500})
    chk('VSI zero points at 9 o\'clock', close(z['ang'],180,12), f"{z['ang']:.0f} deg")
    chk('a climb swings the VSI needle up', 200 < norm(up['ang']) < 320, f"1500 fpm -> {up['ang']:.0f} deg")
    chk('a descent swings it down', 40 < norm(dn['ang']) < 160, f"-1500 fpm -> {dn['ang']:.0f} deg")

    # --- altimeter: the 100 ft needle makes a full turn every 1,000 ft ---
    # The long hundreds needle against a face of ticks and numerals: track it by
    # what changed between two altitudes rather than by brightness.
    a0=await pg.evaluate(PROBE,{'col':2,'row':0,'r':30,'ft':2000})
    a2=await pg.evaluate(PROBE,{'col':2,'row':0,'r':30,'ft':2250})
    a5=await pg.evaluate(PROBE,{'col':2,'row':0,'r':30,'ft':2500})
    a7=await pg.evaluate(PROBE,{'col':2,'row':0,'r':30,'ft':2750})
    p2,p5,p7=moved_to(a0['ring'],a2['ring']),moved_to(a0['ring'],a5['ring']),moved_to(a0['ring'],a7['ring'])
    chk('2,250 ft puts the hundreds needle at 3 o\'clock', close(p2,0,14), f'{p2} deg')
    chk('2,500 ft puts it at 6 o\'clock', close(p5,90,14), f'{p5} deg')
    chk('2,750 ft puts it at 9 o\'clock', close(p7,180,14), f'{p7} deg')
    back=moved_to(a5['ring'],a0['ring'])
    chk('and 2,000 ft puts it back at 12 o\'clock', close(back,270,14), f'{back} deg')
    # One turn per 10,000 ft: 2,000 ft sits at 0.2 of a turn from 12 o'clock, so
    # 342 degrees; 4,500 ft is a further quarter turn, so 72.
    t20=await pg.evaluate(PROBE,{'col':2,'row':0,'r':20,'ft':2000})
    t45=await pg.evaluate(PROBE,{'col':2,'row':0,'r':20,'ft':4500})
    t70=await pg.evaluate(PROBE,{'col':2,'row':0,'r':20,'ft':7000})
    p45=moved_to(t20['ring'],t45['ring']); p70=moved_to(t20['ring'],t70['ring'])
    chk('thousands needle: 4,500 ft is a quarter turn on from 2,000', close(p45,72,14), f'{p45} deg, expected 72')
    chk('thousands needle: 7,000 ft is half a turn on', close(p70,162,14), f'{p70} deg, expected 162')

    # --- heading: the card turns opposite the aircraft, lubber line stays at the top ---
    # The numerals sit every 30 degrees, so a card shift that is a multiple of 30
    # correlates just as well at 0. Use heading changes that are not multiples of
    # 30 and the periodic component cannot explain the answer.
    h0 =await pg.evaluate(PROBE,{'col':1,'row':1,'r':20,'hdg':0})
    h45=await pg.evaluate(PROBE,{'col':1,'row':1,'r':20,'hdg':45})
    h100=await pg.evaluate(PROBE,{'col':1,'row':1,'r':20,'hdg':100})
    k45=best_shift(h0['ring'],h45['ring'])
    k100=best_shift(h0['ring'],h100['ring'])
    chk('heading card turns 45 degrees for a 45 degree heading change',
        close(k45,45,7) or close(k45,315,7), f'card shifted {k45} deg for 045')
    chk('and 100 for 100', close(k100,100,7) or close(k100,260,7), f'card shifted {k100} deg for 100')
    chk('the card turns the same way both times',
        (close(k45,45,7) and close(k100,100,7)) or (close(k45,315,7) and close(k100,260,7)),
        f'{k45} and {k100}')

    await pg.evaluate(PROBE,{'col':0,'row':0,'r':22,'kt':95})
    await pg.evaluate("()=>{const s=window.__kgeu.state();s.vel.y=3.2;s.pos.y=700;s.w.y=-0.052;s.sfR=0.11;s.quat.setFromEuler(new THREE.Euler(0.14,-38*Math.PI/180,-0.30,'YXZ'));window.__kgeu.drawSixPack();}")
    el=await pg.query_selector('#sixpack')
    await el.screenshot(path=f'{SHOTS}/sixpack_closeup.png')

    chk('no console errors', not errs, ' | '.join(errs[:2]))
    await b.close()
  print(f'FAILS {len(fails)}'+((': '+'; '.join(fails)) if fails else ''))
  sys.exit(1 if fails else 0)
asyncio.run(main())
