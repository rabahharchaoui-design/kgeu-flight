# overwatch2 item 5: the ball view's layout with a tasking destination up. OVERWATCH (seed 3) flown to the compound, the
# vehicle leaving and REPORTed so the destination card (#hDest) follows it; then at four phone sizes (568x320, 844x390,
# 932x430, 390x844 portrait), declutter 0/1/2, DTV and IR WHT, Easy and Hard: #hDest shows and names the vehicle, it sits
# under the left block (#shTgt) when that shows, and no element of the ball view (map, the readouts, the dial, the cue,
# the destination, pause, the dock buttons, the caption and task card, the REPORT bar, the top column) overlaps another
# (each rect shrunk 2 px) and all sit on screen. Every state is measured with a long Mission Control caption on the air
# (__kgeu.capTest, held), and the top column's strip (its clipped box in portrait) must clear the left block, the card,
# the dial, the mode lines, the map, pause, the REPLY buttons and the dock, 6 px above the block and the card in portrait.
# A screenshot of every state: /tmp/sensor_layout_<size>_<skill>_<mode>_<dc>.png. No console errors.
# Usage: .venv/bin/python tests/sensor_layout_check.py [--sizes 844x390,...] [--dump]
import asyncio, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, finger

K = 'window.__kgeu'
SIZES = sys.argv[sys.argv.index('--sizes') + 1].split(',') if '--sizes' in sys.argv else ['568x320', '844x390', '932x430', '390x844']
STEP = "(n)=>{for(let i=0;i<n;i++)window.__kgeu.stepFrame(0.1,false,true)}"
SHOW = f"()=>{{const a={K}.task().ask;return !!(a&&a.shown)}}"
async def adv(pg, sec): await pg.evaluate(STEP, max(1, int(sec * 10)))
async def until(pg, cond, maxs=300, step=1):
    for _ in range(int(maxs / step)):
        await adv(pg, step)
        if await pg.evaluate(cond): return True
    return False

# every ball view element on screen now: [name, rect, isText]; text readouts shrink to their glyphs (pre text: a Range)
LAY = """()=>{const W=innerWidth,H=innerHeight,vis=e=>{if(!e)return null;const cs=getComputedStyle(e);if(cs.display==='none'||cs.visibility==='hidden'||+cs.opacity===0)return null;
    const r=e.getBoundingClientRect();return r.width>0&&r.height>0?r:null;};
  const tb=e=>{const r=vis(e);if(!r)return null;const rg=document.createRange();rg.selectNodeContents(e);const rs=[...rg.getClientRects()].filter(q=>q.width>1&&q.height>1);if(!rs.length)return null;
    const g={left:Math.min(...rs.map(q=>q.left)),top:Math.min(...rs.map(q=>q.top)),right:Math.max(...rs.map(q=>q.right)),bottom:Math.max(...rs.map(q=>q.bottom))};
    // a clamped block (the REPORT bar up: #shTR keeps one line) clips its glyphs to its own box
    if(getComputedStyle(e).overflow!=='visible'){g.left=Math.max(g.left,r.left);g.top=Math.max(g.top,r.top);g.right=Math.min(g.right,r.right);g.bottom=Math.min(g.bottom,r.bottom);}
    return g;};
  const $=i=>document.getElementById(i),L=[];
  for(const i of ['shTL','shTR','shTgt','shMid','shBL','shBR'])if($(i).textContent.trim()){const r=tb($(i));if(r)L.push([i,r]);}
  if($('shCue').classList.contains('on')){const r=tb($('shCue'));if(r)L.push(['shCue',r]);}
  for(const i of ['map','shDialW','hDest','bPause','fovInd','stickHint']){const r=vis($(i));if(r)L.push([i,r]);}
  document.querySelectorAll('#uiroot > #dock button').forEach((e,n)=>{const r=vis(e);if(r)L.push(['dock:'+(e.id||n),r]);});
  document.querySelectorAll('#cap > .on, #topCol > .on').forEach((e,n)=>{let r=vis(e);const P=e.parentNode,pr=P.getBoundingClientRect();
    // a clipped column (the portrait ball view's one line strip) shows only what is inside it
    if(r&&getComputedStyle(P).overflow!=='visible'){r={left:Math.max(r.left,pr.left),top:Math.max(r.top,pr.top),right:Math.min(r.right,pr.right),bottom:Math.min(r.bottom,pr.bottom)};if(r.bottom-r.top<3)r=null;}
    if(r)L.push([P.id+'>'+(e.id||n),r]);});
  if($('tkReply').classList.contains('on'))$('tkReply').querySelectorAll('button').forEach((e,n)=>{const r=vis(e);if(r)L.push(['reply:'+(e.dataset.k||n),r]);});
  const bx=r=>[Math.round(r.left),Math.round(r.top),Math.round(r.right),Math.round(r.bottom)];
  const S=L.map(([n,r])=>[n,{left:r.left+2,top:r.top+2,right:r.right-2,bottom:r.bottom-2},r]);
  const bad=[],out=[];
  for(let i=0;i<S.length;i++){const [n,a,ra]=S[i];if(ra.left<0||ra.top<0||ra.right>W||ra.bottom>H)out.push(n+' '+bx(ra));
    for(let j=i+1;j<S.length;j++){const [m,b,rb]=S[j];if(a.left<b.right&&b.left<a.right&&a.top<b.bottom&&b.top<a.bottom)bad.push(n+' '+bx(ra)+' x '+m+' '+bx(rb));}}
  const d=$('hDest'),g=$('shTgt'),dv=vis(d),gv=vis(g);
  const z=vis($('stickZone'));
  // the top column's strip: the clipped column's own box in portrait, the union of what it shows elsewhere
  let strip=null;{const T=$('topCol'),on=[...T.children].filter(e=>e.classList.contains('on')&&vis(e));
    if(on.length){const tr=T.getBoundingClientRect();
      if(getComputedStyle(T).overflow!=='visible')strip=tr;
      else{const rs=on.map(vis);strip={left:Math.min(...rs.map(q=>q.left)),top:Math.min(...rs.map(q=>q.top)),right:Math.max(...rs.map(q=>q.right)),bottom:Math.max(...rs.map(q=>q.bottom))};}}}
  const sbad=[];if(strip){const a={left:strip.left+2,top:strip.top+2,right:strip.right-2,bottom:strip.bottom-2};
    for(const [n,,r] of S){if(/^topCol>/.test(n))continue;if(!/^(shTgt|hDest|shDialW|shTL|map|bPause|reply:|dock:)/.test(n))continue;
      if(a.left<r.right&&r.left<a.right&&a.top<r.bottom&&r.top<a.bottom)sbad.push('strip '+bx(strip)+' x '+n+' '+bx(r));}}
  const atcOn=$('atc').classList.contains('on')&&!!vis($('atc'));
  return {bad,out,names:L.map(a=>a[0]),zone:z?z.top:null,dest:dv?{top:dv.top,bottom:dv.bottom,txt:d.innerText.replace(/\\s+/g,' ').trim(),cut:(()=>{const q=d.querySelector('#dTxt b');return q?q.scrollWidth>q.clientWidth+1:true;})()}:null,tgt:gv?{top:gv.top,bottom:gv.bottom}:null,strip:strip?{top:strip.top,bottom:strip.bottom}:null,sbad,atcOn,atcCls:$('atc').parentNode.id+' '+$('atc').className+' '+$('atc').innerText.slice(0,30)+' '+getComputedStyle($('atc')).display,
    rects:Object.fromEntries(L.map(([n,r])=>[n,bx(r)]))};}"""
CAP = "Copy, vehicle moving. Follow it and keep the ball on it, call any stop or any change of direction, we are watching the feed with you."
CAPP = "The vehicle is moving. Follow it and keep the camera on it."



async def fly(pg, seed):
    await pg.evaluate(f"()=>{{{K}.TASK.test.noBrief=true;{K}.taskStart('overwatch',{{seed:{seed}}})}}")
    await until(pg, SHOW, 30)
    await pg.evaluate(f"()=>{K}.taskAnswer('WILCO')")
    await pg.evaluate(f"()=>{K}.auto()"); await until(pg, f"()=>{K}.state().agl>120", 120)
    await pg.evaluate(f"()=>{K}.auto()")
    await pg.evaluate(f"()=>{{const K={K},s=K.state(),d=K.TASK.d;const a=Math.atan2(s.pos.x-d.c.x,s.pos.z-d.c.z);s.pos.x=d.c.x+Math.sin(a)*2200;s.pos.z=d.c.z+Math.cos(a)*2200;s.pos.y=(3000-1071)/3.28084;}}")
    await adv(pg, 8)
    await finger(pg, '#bSensor'); await adv(pg, 0.3)
    await pg.evaluate(f"()=>{{const K={K};K.SENSOR.slewTo=K.TASK.d.bld;}}"); await adv(pg, 2)
    await pg.evaluate(f"()=>{K}.sensorLock()")
    # the departure brought forward (the layout is the subject), then REPORT: the destination follows the vehicle
    await pg.evaluate(f"()=>{K}.tqStage(2)"); await adv(pg, 0.5)
    await pg.evaluate(f"()=>{{const K={K},d=K.TASK.d;d.dep=K.state().time-d.w0+3;if(d.ppl)d.ppl.tDep=null;}}")
    await until(pg, f"()=>{K}.TASK.d.veh.moving", 30, 0.1)
    await adv(pg, 2)
    await pg.evaluate(f"()=>{K}.taskAnswer('REPORT')"); await adv(pg, 0.5)
    await until(pg, SHOW, 20)


async def main():
    c = Checks(); srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        for sz in SIZES:
            w, h = [int(v) for v in sz.split('x')]
            pg = await page(b, url, vp={'width': w, 'height': h}, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
            if h > w: await pg.evaluate("()=>document.body.classList.add('portraitok')")
            for _ in range(120):
                if (await pg.evaluate(f"()=>{K}.owSlots()"))['n']: break
                await pg.wait_for_timeout(500)
            await fly(pg, 3)
            v = await pg.evaluate(f"()=>{{const K={K},d=K.TASK.d;return {{cap:d.veh.T.cap,short:d.veh.short,moving:d.veh.moving,sens:document.body.classList.contains('sensorOn'),dest:K.dest()}}}}")
            c(f'{sz}: in the ball view, the vehicle moving, the destination following it', v['sens'] and v['moving'] and v['dest'] and v['dest']['name'] == 'The ' + v['short'], v)
            fails = []; n = 0
            for skill in ('pilot', 'rookie'):
                await pg.evaluate(f"()=>{K}.setSkill('{skill}')")
                for mode in ('tv', 'irw'):
                    await pg.evaluate(f"()=>{K}.setSensorMode('{mode}')")
                    for dc in (0, 1, 2):
                        await pg.evaluate(f"()=>{{const K={K};while((K.SENSOR.dclt||0)!=={dc})K.sensorDclt();}}")
                        await adv(pg, 0.3)
                        await pg.evaluate("()=>{const t=document.getElementById('toast');t&&t.classList.remove('on');}")
                        await pg.evaluate(f"()=>{K}.capTest({CAP!r},{CAPP!r})")
                        await pg.evaluate("()=>window.__kgeu.stepFrame(1/60,false,false)"); await pg.wait_for_timeout(60)
                        o = await pg.evaluate(LAY); n += 1
                        tag = f'{sz} {"Hard" if skill == "pilot" else "Easy"} {mode.upper()} dc{dc}'
                        d = o['dest']
                        want = ('the ' + v['short']) if skill == 'rookie' else v['cap']
                        why = []
                        if not d: why.append('#hDest not shown')
                        elif want.lower() not in d['txt'].lower(): why.append(f'#hDest "{d["txt"]}" does not name {want}')
                        if d and d['cut']: why.append(f'#hDest name cut short ({d["txt"]})')
                        if d and o['tgt'] and d['top'] < o['tgt']['bottom'] + 6: why.append(f'#hDest top {d["top"]:.0f} < #shTgt bottom {o["tgt"]["bottom"]:.0f} + 6')
                        if d and o['zone'] is not None and o['zone'] < d['bottom'] - 1: why.append(f'the slew zone (top {o["zone"]:.0f}) starts over #hDest (bottom {d["bottom"]:.0f})')
                        # on the smallest landscape screen hudFit holds the caption (no room for it above 26% clear of the
                        # buttons; it comes back when there is): on the air but not drawn, so nothing to overlap
                        held = h < w and ' hold ' in o['atcCls'] + ' '
                        if not held and (not o['atcOn'] or not o['strip']): why.append('the Mission Control caption is not on the air: ' + o['atcCls'])
                        if o['sbad']: why.append('top column strip overlap: ' + '; '.join(o['sbad']))
                        if h > w and o['strip']:
                            for k, r in (('#shTgt', o['tgt']), ('#hDest', d)):
                                if r and r['top'] < o['strip']['bottom'] + 6: why.append(f'{k} top {r["top"]:.0f} < strip bottom {o["strip"]["bottom"]:.0f} + 6')
                        if h > w:   # no bounce: the strip's row stays reserved, so the block and the card do not move when the caption goes
                            await pg.evaluate("()=>{document.getElementById('atc').style.display='none';window.__kgeu.stepFrame(1/60,false,false)}"); await pg.wait_for_timeout(60)
                            q = await pg.evaluate(LAY)
                            await pg.evaluate("()=>{document.getElementById('atc').style.display=''}")
                            for k in ('tgt', 'dest'):
                                if (o[k] and o[k]['top']) != (q[k] and q[k]['top']): why.append(f'{k} moves when the caption goes off the air ({o[k]} to {q[k]})')
                        if o['bad']: why.append('overlap: ' + '; '.join(o['bad']))
                        if o['out']: why.append('off screen: ' + '; '.join(o['out']))
                        if why: fails.append((tag, why))
                        if sz == SIZES[0] and n == 1: print('  elements:', ', '.join(o['names']))
                        if '--dump' in sys.argv: print('  ', tag, o['rects'])
                        await pg.screenshot(path=f'/tmp/sensor_layout_{sz}_{skill}_{mode}_{dc}.png')
            c(f'{sz}: 12 states (Easy/Hard, DTV/IR WHT, DCLT 0/1/2): #hDest shows and names the vehicle, sits under #shTgt, nothing overlaps, all on screen', not fails, fails[:4])
            c(f'{sz}: no console errors', not pg.errs, pg.errs[:3])
            await pg.close()
        await b.close()
    srv.shutdown(); c.done('sensor_layout_check')

asyncio.run(main())
