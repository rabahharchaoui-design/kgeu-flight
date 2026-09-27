# Spawn picker: the F-16 starts at Luke, everything else at Glendale, and either
# aircraft can be sent to either field.
import asyncio, os, sys, json
from playwright.async_api import async_playwright
THREE=open('node_modules/three/build/three.min.js').read()
URL='file://'+os.path.abspath('index.html')
SHOTS=os.path.abspath('overnight-screenshots')
fails=[]
def chk(n,c,d=''):
    print(('  ok   ' if c else '  FAIL ')+n+(('  '+d) if d else ''))
    if not c: fails.append(n)
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(args=['--use-gl=swiftshader','--enable-unsafe-swiftshader'])
    ctx=await b.new_context(viewport={'width':844,'height':390},is_mobile=True,has_touch=True,device_scale_factor=2)
    pg=await ctx.new_page(); errs=[]
    pg.on('pageerror',lambda e:errs.append(str(e)))
    await pg.route('**/three.min.js',lambda r:r.fulfill(body=THREE,content_type='application/javascript'))
    await pg.route('**/fonts.googleapis.com/**',lambda r:r.abort())
    await pg.goto(URL); await pg.wait_for_timeout(2500)

    async def spawn(t,base=None):
        await pg.evaluate(f"()=>window.__kgeu.pick('{t}')")
        if base: await pg.evaluate(f"()=>window.__kgeu.pickBase('{base}')")
        await pg.evaluate("()=>window.__kgeu.start('runway')")
        await pg.wait_for_timeout(1400)
        return await pg.evaluate("""()=>{const K=window.__kgeu,s=K.state();
          const L=K.lukeUV(s.pos.x,s.pos.z);
          return {base:s.base,x:s.pos.x,z:s.pos.z,lukeU:L[0],lukeV:L[1],
                  distLuke:Math.hypot(s.pos.x-K.LUKE.x,s.pos.z-K.LUKE.z),
                  distKgeu:Math.hypot(s.pos.x,s.pos.z),crashed:s.crashed};}""")

    r=await spawn('f16')
    chk('F-16 defaults to Luke', r['base']=='luke' and r['distLuke']<2000, json.dumps({k:round(v,0) if isinstance(v,float) else v for k,v in r.items()}))
    chk('F-16 sits on Luke runway 03L', abs(r['lukeV']+152.5)<30 and r['lukeU']<-1400, f"u {r['lukeU']:.0f} v {r['lukeV']:.0f}")
    await pg.screenshot(path=f'{SHOTS}/base_f16_luke.png')

    r=await spawn('cessna')
    chk('C172 defaults to Glendale', r['base']=='kgeu' and r['distKgeu']<400, f"base {r['base']} dist {r['distKgeu']:.0f} m")

    r=await spawn('c130','luke')
    chk('C-130 can be sent to Luke', r['base']=='luke' and r['distLuke']<2000, f"base {r['base']} dist {r['distLuke']:.0f} m")
    chk('C-130 at Luke is not crashed', not r['crashed'])

    r=await spawn('f16','kgeu')
    chk('F-16 can be sent to Glendale', r['base']=='kgeu' and r['distKgeu']<400, f"base {r['base']} dist {r['distKgeu']:.0f} m")

    # picking an aircraft resets to its home field
    await pg.evaluate("()=>window.__kgeu.pick('f16')")
    bb=await pg.evaluate("()=>window.__kgeu.base()")
    chk('picking the F-16 again resets it to Luke', bb=='luke', bb)

    # ramp and final work at Luke too
    await pg.evaluate("()=>{window.__kgeu.pick('f16');window.__kgeu.start('ramp');}")
    await pg.wait_for_timeout(1400)
    r=await pg.evaluate("""()=>{const K=window.__kgeu,s=K.state();return {base:s.base,paved:K.isPaved(s.pos.x,s.pos.z),crashed:s.crashed};}""")
    chk('Luke ramp start is on pavement', r['base']=='luke' and r['paved'] and not r['crashed'], json.dumps(r))
    await pg.evaluate("()=>window.__kgeu.start('final')")
    await pg.wait_for_timeout(1400)
    r=await pg.evaluate("""()=>{const K=window.__kgeu,s=K.state();const L=K.lukeUV(s.pos.x,s.pos.z);
      return {agl:s.agl,lukeU:L[0],lukeV:L[1],crashed:s.crashed};}""")
    chk('Luke 3 mile final is lined up on 03L', abs(r['lukeV']+152.5)<60 and -7200<r['lukeU']<-6300 and not r['crashed'],
        f"u {r['lukeU']:.0f} v {r['lukeV']:.0f} agl {r['agl']:.0f} m")
    chk('Luke final is above the ground', 250<r['agl']<330, f"{r['agl']:.0f} m")
    await pg.screenshot(path=f'{SHOTS}/base_luke_final.png')

    chk('no console errors', not errs, ' | '.join(errs[:2]))
    await b.close()
  print(f'FAILS {len(fails)}'+((': '+'; '.join(fails)) if fails else ''))
  sys.exit(1 if fails else 0)
asyncio.run(main())
