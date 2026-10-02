# Phone2 item 9: the pause sheet. A top bar with a big RESUME, Restart / Apply and MAIN MENU on its
# own at the far right (secondary style), then two panels: nav (Missions, Arcade, School, Boards),
# the quick tiles (Sound, Invert, Stick) and the music row on the left; mode, Action Shot, Settings,
# the aircraft, base, time and starts on the right. Every target 44 px, at least 12 px between
# neighbouring buttons, nothing cut off, no scrolling, at 568x320, 667x375, 844x390 and 390x844.
# Screenshots: overnight-screenshots/phone2/menus/after_pause_*.png. Run: .venv/bin/python tests/pause_layout_check.py
import asyncio, os, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, finger
ok = Checks()
K = 'window.__kgeu'
SIZES = [(568, 320), (667, 375), (844, 390), (390, 844)]
AUDIT = """()=>{const ov=document.getElementById('pauseOv'),pz=ov.querySelector('.pz');const W=innerWidth,H=innerHeight;const bad=[];
  // the location row scrolls sideways (4.6b): a card counts by the part its row shows, a card scrolled out of sight not at all
  const R=b=>{const r=b.getBoundingClientRect(),L=b.closest('.locs');if(!L)return r;const q=L.getBoundingClientRect(),x0=Math.max(r.left,q.left),x1=Math.max(x0,Math.min(r.right,q.right));
    return {left:x0,right:x1,top:r.top,bottom:r.bottom,x:x0,y:r.top,width:x1-x0,height:r.height};};
  const bs=[...ov.querySelectorAll('button')].filter(b=>R(b).width>0.5&&getComputedStyle(b).visibility!=='hidden');
  bs.forEach(b=>{const r0=b.getBoundingClientRect(),r=R(b),id=b.id||b.textContent.trim().slice(0,12);
    if(r0.width<43.5||r0.height<43.5)bad.push('small '+id+' '+Math.round(r0.width)+'x'+Math.round(r0.height));
    if(r.left<-0.5||r.top<-0.5||r.right>W+0.5||r.bottom>H+0.5)bad.push('off screen '+id);
    if(b.scrollWidth>b.clientWidth+1)bad.push('text cut '+id);
    b.querySelectorAll('b,i,span').forEach(e=>{if(e.offsetParent&&e.scrollWidth>e.clientWidth+1)bad.push('truncated '+e.textContent.trim().slice(0,12));});});
  // neighbours: 12 px between any two buttons, 8 px between the chips of one segmented group (aircraft,
  // base, time, starts, Easy/Hard) on the 568 wide screen; overlaps never
  let minGap=1e9,minIn=1e9;const grp=b=>b.closest('.acRow,.modeSeg,.pzQ,.frow');   // one row of chips or tiles is one group
  for(let i=0;i<bs.length;i++)for(let j=i+1;j<bs.length;j++){const a=R(bs[i]),b=R(bs[j]);if(bs[i].contains(bs[j])||bs[j].contains(bs[i]))continue;
    const gx=Math.max(a.left,b.left)-Math.min(a.right,b.right),gy=Math.max(a.top,b.top)-Math.min(a.bottom,b.bottom);
    const ox=-gx>0.5,oy=-gy>0.5;if(ox&&oy)bad.push('overlap '+(bs[i].id||bs[i].textContent.trim().slice(0,8))+'/'+(bs[j].id||bs[j].textContent.trim().slice(0,8)));
    else{const g=ox?gy:oy?gx:Math.max(gx,gy);const same=grp(bs[i])&&grp(bs[i])===grp(bs[j]);if(same){if(g<minIn)minIn=g;}else if(g<minGap)minGap=g;}}
  const scroll=[...ov.querySelectorAll('*')].some(e=>{const cs=getComputedStyle(e);return (cs.overflowY==='auto'||cs.overflowY==='scroll')&&e.scrollHeight>e.clientHeight+1;})||ov.scrollHeight>ov.clientHeight+1;
  const r=id=>{const e=document.getElementById(id);const q=e.getBoundingClientRect();return {x:q.x,y:q.y,w:q.width,h:q.height,r:q.right,b:q.bottom};};
  const order=['pResume','pApply','pMenu','pMis','pArc','pSch','pLb','pSound','pInv','pSens','pPrev','pMusic','pMnext','pPhoto','pSet'].map(r);
  const menu=r('pMenu'),res=r('pResume');
  const near=bs.filter(b=>b.id!=='pMenu').map(b=>{const q=R(b);const gx=Math.max(q.left,menu.x)-Math.min(q.right,menu.r),gy=Math.max(q.top,menu.y)-Math.min(q.bottom,menu.b);return Math.max(gx,gy);});
  return {bad:bad,minGap:+minGap.toFixed(1),minIn:+minIn.toFixed(1),scroll:scroll,n:bs.length,
    resumeTop:res.y<=Math.min(...order.map(o=>o.y))+0.5,resumeBig:res.w>=1.4*r('pApply').w,
    menuRight:menu.r>=Math.max(...order.map(o=>o.r))-0.5,menuApart:Math.min(...near),menuSecondary:getComputedStyle(document.getElementById('pMenu')).backgroundColor!==getComputedStyle(document.getElementById('pResume')).backgroundColor,
    navRow:['pMis','pArc','pSch','pLb'].map(id=>r(id)),tiles:['pSound','pInv','pSens'].map(id=>r(id)),music:['pPrev','pMusic','pMnext'].map(id=>r(id)),
    acChips:document.querySelectorAll('#pAc .pick').length,labels:['pMis','pArc','pSch','pLb','pMenu','pResume'].map(id=>document.getElementById(id).textContent.trim())}}"""

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        for W, H in SIZES:
            pg = await page(b, url, vp={'width': W, 'height': H}, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
            await pg.evaluate(f"()=>{{const r=document.getElementById('rotOk');if(r&&r.offsetParent)r.click();const K={K};K.pick('f16');K.pickBase('kgeu');K.start('runway');}}"); await pg.wait_for_timeout(600)
            await finger(pg, '#bPause'); await pg.wait_for_timeout(600)
            a = await pg.evaluate(AUDIT)
            tag = f'{W}x{H}'
            ok(f'{tag}: 44 px targets, nothing cut off, no overlaps', not a['bad'], a['bad'][:6])
            ok(f'{tag}: at least 12 px between neighbouring buttons', a['minGap'] >= 11.5, a['minGap'])
            ok(f'{tag}: chips or tiles inside one row at least {8 if W < 620 else 12} px apart', a['minIn'] >= (7.5 if W < 620 else 11.5), a['minIn'])
            ok(f'{tag}: no scrolling', not a['scroll'])
            ok(f'{tag}: RESUME is the big one at the top', a['resumeTop'] and a['resumeBig'])
            ok(f'{tag}: MAIN MENU sits on its own at the far right, secondary style, clear of everything', a['menuRight'] and a['menuApart'] >= 11.5 and a['menuSecondary'], (a['menuRight'], a['menuApart'], a['menuSecondary']))
            ok(f'{tag}: nav row Missions, Arcade, School, Boards; MAIN MENU and RESUME labelled', a['labels'] == ['Missions', 'Arcade', 'School', 'Boards', 'MAIN MENU', 'RESUME'], a['labels'])
            ok(f'{tag}: the quick tiles and the music row are rows (same top)', len({round(t['y']) for t in a['tiles']}) == 1 and len({round(t['y']) for t in a['music']}) == 1, (a['tiles'], a['music']))
            ok(f'{tag}: six aircraft chips', a['acChips'] == 6, a['acChips'])
            # order: nav above tiles above music (left panel); mode row above aircraft above base/time above starts (right)
            ok(f'{tag}: nav, then tiles, then music, top to bottom', a['navRow'][0]['y'] < a['tiles'][0]['y'] < a['music'][0]['y'])
            await pg.screenshot(path=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'overnight-screenshots', 'phone2', 'menus', f'after_pause_{tag}.png'))
            # every button does something: Resume, and the aircraft chip then Apply
            await finger(pg, '#pAc .pick[data-t="cessna"]'); await pg.wait_for_timeout(200)
            lbl = await pg.evaluate("()=>document.getElementById('pApply').textContent")
            ok(f'{tag}: picking an aircraft turns Restart into Apply', lbl == 'Apply', lbl)
            await finger(pg, '#pApply'); await pg.wait_for_timeout(1200)
            ok(f'{tag}: Apply flies the pick', await pg.evaluate(f"()=>{K}.state().type==='cessna'&&{K}.running()&&!{K}.paused()"))
            await finger(pg, '#bPause'); await pg.wait_for_timeout(500)
            await finger(pg, '#pResume'); await pg.wait_for_timeout(300)
            ok(f'{tag}: RESUME resumes', await pg.evaluate(f"()=>!{K}.paused()&&!document.getElementById('pauseOv').classList.contains('on')"))
            await finger(pg, '#bPause'); await pg.wait_for_timeout(500)
            await finger(pg, '#pMenu'); await pg.wait_for_timeout(500)
            ok(f'{tag}: MAIN MENU goes home', await pg.evaluate(f"()=>document.getElementById('menu').classList.contains('on')&&{K}.curScr()==='sHome'"))
            ok(f'{tag}: no page errors', not pg.errs, pg.errs[:3])
            await pg.context.close()
        await b.close()
    sys.exit(ok.done('pause_layout_check'))

asyncio.run(main())
