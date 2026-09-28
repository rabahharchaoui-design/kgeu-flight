# Feature 9: photo mode. Run: .venv/bin/python tests/photo_check.py
import asyncio, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, finger
ok = Checks()
K = "window.__kgeu"
SHARE = """(()=>{window.__shared=null;navigator.canShare=f=>!!(f&&f.files&&f.files.length);
  navigator.share=d=>{window.__shared=d.files[0];return Promise.resolve();};})()"""
async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1'})
        await pg.context.add_init_script(SHARE); await pg.reload(); await pg.wait_for_function('()=>window.__kgeu'); await pg.wait_for_timeout(400)
        await pg.evaluate(f"()=>{{{K}.pick('f16');{K}.pickBase('luke');{K}.start('final')}}"); await pg.wait_for_timeout(1500)
        await finger(pg, '#bPause'); await pg.wait_for_timeout(300)
        ok('the pause sheet has a Photo button with a camera icon', await pg.evaluate("()=>{const b=document.getElementById('pPhoto');return !!b.querySelector('svg')&&b.getBoundingClientRect().height>=44}"))
        await finger(pg, '#pPhoto'); await pg.wait_for_timeout(500)
        s = await pg.evaluate(f"""()=>({{photo:{K}.PHOTO.on,paused:{K}.paused(),hud:getComputedStyle(document.getElementById('uiroot')).display,
          pause:document.getElementById('pauseOv').classList.contains('on')}})""")
        ok('photo mode freezes the frame and hides the HUD', s == {'photo': True, 'paused': True, 'hud': 'none', 'pause': False}, s)
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
        f = await pg.evaluate("""async()=>{const f=window.__shared;if(!f)return null;const bm=await createImageBitmap(f);
          const c=document.createElement('canvas');c.width=bm.width;c.height=bm.height;const x=c.getContext('2d');x.drawImage(bm,0,0);
          const d=x.getImageData(0,0,bm.width,bm.height).data;let mn=255,mx=0;for(let i=0;i<d.length;i+=4*97){const v=d[i]+d[i+1]+d[i+2];mn=Math.min(mn,v);mx=Math.max(mx,v);}
          // the watermark corner should hold sand coloured text pixels
          const w=x.getImageData(bm.width*0.7,bm.height*0.88,bm.width*0.29,bm.height*0.1).data;let sand=0;
          for(let i=0;i<w.length;i+=4)if(Math.abs(w[i]-246)<40&&Math.abs(w[i+1]-193)<40&&Math.abs(w[i+2]-119)<45)sand++;
          return {type:f.type,name:f.name,size:f.size,w:bm.width,h:bm.height,range:mx-mn,sand:sand}}""")
        ok('SAVE hands a PNG to the share sheet', f and f['type'] == 'image/png' and f['name'].startswith('pocket-flight-sim'), f)
        ok('the image is the real frame, not blank', f and f['range'] > 150 and f['w'] > 600, f)
        ok('it carries the Pocket Flight Sim watermark in the corner', f and f['sand'] > 150, f)
        await finger(pg, '#phX'); await pg.wait_for_timeout(300)
        ok('closing photo mode returns to the pause sheet', await pg.evaluate(f"()=>!{K}.PHOTO.on&&document.getElementById('pauseOv').classList.contains('on')"))
        ok('no page errors', not pg.errs, pg.errs[:3])
        await b.close()
    sys.exit(ok.done('photo_check'))
asyncio.run(main())
