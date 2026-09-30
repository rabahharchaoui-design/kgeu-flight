# Feature 9 / phone item 18: photo mode, now the Action Shot. Run: .venv/bin/python tests/photo_check.py
import asyncio, json, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, finger
ok = Checks()
K = "window.__kgeu"
# The stub records whether navigator.share was called synchronously inside the tap's click handler:
# the trusted click is still window.event and photoSave (the handler) is a live, non async frame on the
# call stack. A share deferred to a promise callback, an await or a toBlob callback fails one or both.
# It also records navigator.userActivation.isActive at the moment of the call.
TAP = """(()=>{window.__dl=null;
  document.addEventListener('click',e=>{const a=e.target;if(a&&a.tagName==='A'&&a.download){window.__dl={name:a.download,len:a.href.length,png:a.href.startsWith('data:image/png')};e.preventDefault();}},true);})()"""
SHARE = """(()=>{window.__shared=null;navigator.canShare=f=>!!(f&&f.files&&f.files.length);
  navigator.share=d=>{window.__shared={file:d.files[0],title:d.title,text:d.text,inTap:!!(window.event&&window.event.type==='click'&&window.event.isTrusted)&&/\\bat (?!async )\\S*photoSave\\b/.test(new Error().stack),
    active:!!(navigator.userActivation&&navigator.userActivation.isActive)};return Promise.resolve();};})()"""
NOSHARE = """(()=>{try{delete Navigator.prototype.share;delete Navigator.prototype.canShare;}catch(e){}
  navigator.share=undefined;navigator.canShare=undefined;})()"""
IMG = """async(f)=>{if(!f)return null;const bm=await createImageBitmap(f);
  const c=document.createElement('canvas');c.width=bm.width;c.height=bm.height;const x=c.getContext('2d');x.drawImage(bm,0,0);
  const d=x.getImageData(0,0,bm.width,bm.height).data;let mn=255,mx=0;for(let i=0;i<d.length;i+=4*97){const v=d[i]+d[i+1]+d[i+2];mn=Math.min(mn,v);mx=Math.max(mx,v);}
  // the watermark corner should hold sand coloured text pixels
  const w=x.getImageData(bm.width*0.7,bm.height*0.88,bm.width*0.29,bm.height*0.1).data;let sand=0;
  for(let i=0;i<w.length;i+=4)if(Math.abs(w[i]-246)<40&&Math.abs(w[i+1]-193)<40&&Math.abs(w[i+2]-119)<45)sand++;
  const gl=document.getElementById('gl');
  return {type:f.type,name:f.name,size:f.size,w:bm.width,h:bm.height,glw:gl.width,glh:gl.height,range:mx-mn,sand:sand}}"""
SEED = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuLB': json.dumps({'cs': 'MESQUITE', 'key': 'ab' * 24, 'xp': 0})}

async def fly(pg, stub):
    await pg.context.add_init_script(TAP); await pg.context.add_init_script(stub)
    await pg.reload(); await pg.wait_for_function('()=>window.__kgeu'); await pg.wait_for_timeout(400)
    await pg.evaluate(f"()=>{{{K}.pick('f16');{K}.pickBase('luke');{K}.start('final')}}"); await pg.wait_for_timeout(1500)
    await finger(pg, '#bPause'); await pg.wait_for_timeout(300)

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, storage=SEED)
        await fly(pg, SHARE)
        s = await pg.evaluate("""()=>{const b=document.getElementById('pPhoto'),r=b.getBoundingClientRect();
          return {text:b.textContent.trim(),svg:!!b.querySelector('svg'),h:r.height,w:r.width,fits:b.scrollWidth<=b.clientWidth+1}}""")
        ok('the pause sheet button reads "Action Shot" with a camera icon, 44 pt tall, text fits', s['text'] == 'Action Shot' and s['svg'] and s['h'] >= 44 and s['fits'], s)
        ok('no "Photo" label is left in the pause sheet or the overlay', await pg.evaluate(
            "()=>!/\\bPhoto\\b/.test(document.getElementById('pauseOv').innerText+document.getElementById('photoOv').innerHTML)"))
        await finger(pg, '#pPhoto'); await pg.wait_for_timeout(500)
        s = await pg.evaluate(f"""()=>({{photo:{K}.PHOTO.on,paused:{K}.paused(),hud:getComputedStyle(document.getElementById('uiroot')).display,
          pause:document.getElementById('pauseOv').classList.contains('on')}})""")
        ok('the Action Shot freezes the frame and hides the HUD', s == {'photo': True, 'paused': True, 'hud': 'none', 'pause': False}, s)
        s = await pg.evaluate("()=>{const b=document.getElementById('phSave'),r=b.getBoundingClientRect(),x=document.getElementById('phX').getBoundingClientRect();return {t:b.textContent.trim(),h:r.height,xw:x.width,xh:x.height}}")
        ok('the overlay button reads SHARE when the share sheet is there; 44 pt targets', s['t'] == 'SHARE' and s['h'] >= 44 and s['xw'] >= 44 and s['xh'] >= 44, s)
        p0 = await pg.evaluate(f"()=>{K}.state().pos.toArray()")
        c0 = await pg.evaluate(f"()=>{K}.camPos()")
        await pg.evaluate("""()=>{const c=document.getElementById('photoPad'),ev=(t,x)=>c.dispatchEvent(new PointerEvent(t,{pointerId:2,clientX:x,clientY:180,bubbles:true}));
          ev('pointerdown',200);for(let i=1;i<=8;i++)ev('pointermove',200+i*25);ev('pointerup',400);}""")
        await pg.wait_for_timeout(500)
        c1 = await pg.evaluate(f"()=>{K}.camPos()")
        moved = sum((a-b)**2 for a, b in zip(c0, c1)) ** 0.5
        ok('a finger drag orbits the camera', moved > 5, f'{moved:.1f} m')
        d0 = await pg.evaluate(f"()=>{K}.PHOTO.dist")
        await pg.evaluate("""()=>{const c=document.getElementById('photoPad'),H=180,ev=(t,id,x)=>c.dispatchEvent(new PointerEvent(t,{pointerId:id,clientX:x,clientY:H,bubbles:true}));
          ev('pointerdown',5,300);ev('pointerdown',6,360);for(let i=1;i<=5;i++){ev('pointermove',5,300-i*20);ev('pointermove',6,360+i*20);}ev('pointerup',5,200);ev('pointerup',6,460);}""")
        ok('pinch zooms in', await pg.evaluate(f"()=>{K}.PHOTO.dist") < d0 * 0.8)
        ok('the aircraft stays frozen', await pg.evaluate(f"()=>{K}.state().pos.toArray()") == p0)
        await finger(pg, '#phSave'); await pg.wait_for_timeout(800)
        sh = await pg.evaluate("()=>window.__shared&&{title:window.__shared.title,text:window.__shared.text,inTap:window.__shared.inTap,active:window.__shared.active}")
        ok('share is called synchronously inside the tap, with user activation live', sh and sh['inTap'] and sh['active'], sh)
        ok('the share text carries the game link and the callsign', sh and 'https://rabahharchaoui-design.github.io/kgeu-flight/' in sh['text'] and 'MESQUITE' in sh['text'] and sh['title'] == 'Pocket Flight Sim', sh)
        f = await pg.evaluate(f"()=>({IMG})(window.__shared&&window.__shared.file)")
        ok('SHARE hands a non-empty PNG file to the share sheet', f and f['type'] == 'image/png' and f['name'].startswith('pocket-flight-sim') and f['size'] > 20000, f)
        ok('the image is the full frame at the drawing buffer size', f and f['w'] == f['glw'] and f['h'] == f['glh'] and f['w'] > 600, f)
        ok('the image is the real frame, not blank', f and f['range'] > 150, f)
        ok('it carries the Pocket Flight Sim watermark in the corner', f and f['sand'] > 150, f)
        ok('no download when the share sheet took it', await pg.evaluate("()=>window.__dl===null"))
        await finger(pg, '#phX'); await pg.wait_for_timeout(300)
        ok('closing returns to the pause sheet', await pg.evaluate(f"()=>!{K}.PHOTO.on&&document.getElementById('pauseOv').classList.contains('on')"))
        ok('no page errors', not pg.errs, pg.errs[:3])
        await pg.context.close()

        # no Web Share (a desktop browser): the button reads SAVE and the PNG downloads
        pg = await page(b, url, storage=SEED)
        await fly(pg, NOSHARE)
        await finger(pg, '#pPhoto'); await pg.wait_for_timeout(500)
        ok('without Web Share the overlay button reads SAVE', await pg.evaluate("()=>document.getElementById('phSave').textContent.trim()") == 'SAVE')
        await finger(pg, '#phSave'); await pg.wait_for_timeout(800)
        dl = await pg.evaluate("()=>window.__dl")
        ok('the fallback downloads a PNG through an a[download] link', dl and dl['png'] and dl['name'].startswith('pocket-flight-sim') and dl['name'].endswith('.png') and dl['len'] > 20000, dl)
        f = await pg.evaluate(f"()=>({IMG})(window.__lastPhoto)")
        ok('the downloaded image is the full frame', f and f['w'] == f['glw'] and f['range'] > 150, f)
        ok('no page errors (fallback)', not pg.errs, pg.errs[:3])
        await b.close()
    sys.exit(ok.done('photo_check'))
asyncio.run(main())
