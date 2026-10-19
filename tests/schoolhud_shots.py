# Schoolhud: the in-flight layout of the voice caption and the task card, before and after, in the five modes the owner
# named: the pattern lesson (Dana's correction on the air), the mock checkride (Frank), the OVERWATCH tasking, the C-130
# airdrop (the one minute call) and a dogfight, each at sunset and at night.
# Usage: .venv/bin/python tests/schoolhud_shots.py <outdir> [pattern ride overwatch airdrop dogfight] [--sizes 844x390,568x320]
#        [--tods sunset,night]
# Writes <outdir>/<scene>_<tod>_<W>x<H>.png. Run it from a worktree to shoot that build (harness serves its own root).
import asyncio, os, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, PLACED

_av = sys.argv[1:]
args = [a for i, a in enumerate(_av) if not a.startswith('--') and not (i and _av[i - 1] in ('--sizes', '--tods'))]
OUT = os.path.abspath(args[0] if args else 'overnight-screenshots/schoolhud/after')
SCENES = args[1:] or ['pattern', 'ride', 'overwatch', 'airdrop', 'dogfight']
def opt(k, d): return _av[_av.index(k) + 1].split(',') if k in _av else d
SIZES = [tuple(map(int, s.split('x'))) for s in opt('--sizes', ['844x390'])]
TODS = opt('--tods', ['sunset', 'night'])
K = 'window.__kgeu'
STORE = dict({'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'}, **PLACED)

# the airdrop run in, lifted from fix2_hud_shots (3 nm out on the wind line, 1,000 ft, 140 kt)
PLACE_DZ = f"""()=>{{const K={K},D=K.DZ,s=K.state(),f=D.f,x=D.rel.x-f.x*4828,z=D.rel.z-f.z*4828,gh=K.groundHeight?K.groundHeight(x,z):0;
  const V=140/1.94384;s.pos.set(x,(gh||0)+305+2,z);s.vel.set(f.x*V,0,f.z*V);s.quat.setFromEuler(new THREE.Euler(0.03,-Math.atan2(f.x,-f.z),0,'YXZ'));
  s.w.set(0,0,0);s.throttle=s.power=0.36;s.flapIdx=1;s.trim=0.5;s.airTime=30;s.onGround=false;s.gearDown=false;s.gearPos=0;s.ap=null;}}"""
STEER = f"""(n)=>{{const K={K},s=K.state(),D=K.DZ;for(let k=0;k<n;k++){{if(!K.MISS.dropped){{
    const f=D.f,dx=s.pos.x-D.rel.x,dz=s.pos.z-D.rel.z,c=-dx*f.z+dz*f.x,sp=Math.hypot(s.vel.x,s.vel.z);
    s.pos.x-=-f.z*c*0.5;s.pos.z-=f.x*c*0.5;s.vel.x=f.x*sp;s.vel.z=f.z*sp;
    s.quat.setFromEuler(new THREE.Euler(new THREE.Euler().setFromQuaternion(s.quat,'YXZ').x,-Math.atan2(f.x,-f.z),0,'YXZ'));}}
  for(let j=0;j<15;j++){{K.stepFrame(1/30,false,true);
    if(!K.MISS.dropped){{const gh=K.groundHeight(s.pos.x,s.pos.z);s.pos.y+=(gh+305-s.pos.y)*0.05;}}}}}}
  return {{c1:D.c1}};}}"""
# real frames until the caption is up (or n frames), then a layout pass
SETTLE = f"""(n)=>{{const K={K};for(let i=0;i<n;i++){{K.stepFrame(1/30);const a=document.getElementById('atc');if(a&&a.classList.contains('on')&&i>3)break;}}K.hudFit();}}"""


async def shot(pg, name):
    await pg.wait_for_timeout(450)   # the caption's fade in
    path = os.path.join(OUT, name)
    await pg.screenshot(path=path, timeout=120000)
    print('  wrote', path)


async def pattern(pg, tod):
    await pg.evaluate(f"()=>{{const K={K};K.radioLog(true);K.startLesson('pattern',true);K.lesBriefSkip();K.setTOD('{tod}');}}")
    await pg.wait_for_timeout(300)
    # past the opening call: airborne in the climb out, then the step to the crosswind turn and Dana's altitude correction
    await pg.evaluate(f"""()=>{{const K={K},s=K.state();for(let i=0;i<20;i++)K.stepFrame(0.1,false,true);
      K.radioQ().length=0;K.LES.ph=1;s.onGround=false;s.pos.y+=200;s.vel.y=0;K.stepFrame(1/30);
      K.cfi(K.cfiCue('alt',670));}}""")
    await pg.evaluate(SETTLE, 12)


async def ride(pg, tod):
    await pg.evaluate(f"()=>{{const K={K};K.rideSeed(42);K.radioLog(true);K.startLesson('ride');K.lesBriefSkip();K.setTOD('{tod}');const s=K.state();s.windKt=0;s.gustAmp=0;}}")
    await pg.wait_for_timeout(300)
    await pg.evaluate(f"()=>{{const K={K};for(let i=0;i<30;i++)K.stepFrame(0.1,false,true);}}")
    await pg.evaluate(SETTLE, 12)


async def overwatch(pg, tod):
    await pg.evaluate(f"()=>{{const K={K};K.radioLog(true);K.taskStart('overwatch',{{seed:42}});}}")
    await pg.wait_for_timeout(500)
    await pg.evaluate(f"()=>{{const K={K};K.taskGo();K.setTOD('{tod}');}}")
    await pg.wait_for_timeout(300)
    await pg.evaluate(f"()=>{{const K={K};for(let i=0;i<60;i++)K.stepFrame(0.1,false,true);}}")
    await pg.evaluate(SETTLE, 20)


async def airdrop(pg, tod):
    await pg.evaluate(f"()=>{{const K={K};K.radioLog(true);K.mission('drop');K.setTOD('{tod}');}}")
    await pg.wait_for_timeout(300)
    await pg.evaluate(PLACE_DZ)
    for i in range(16):
        if (await pg.evaluate(STEER, 5))['c1']: break
    await pg.evaluate(SETTLE, 20)


async def dogfight(pg, tod):
    await pg.evaluate(f"()=>{{const K={K};K.DF.test.noBrief=true;K.DF.test.noBanditFire=true;K.dfStart();K.setTOD('{tod}');}}")
    await pg.evaluate(f"()=>{{for(let j=0;j<40;j++)window.__kgeu.stepFrame(1/30);}}")
    await pg.evaluate(SETTLE, 30)


async def main():
    os.makedirs(OUT, exist_ok=True)
    srv, url = serve()
    fns = dict(pattern=pattern, ride=ride, overwatch=overwatch, airdrop=airdrop, dogfight=dogfight)
    async with async_playwright() as p:
        b = await launch(p)
        for w, h in SIZES:
            for sc in SCENES:
                for tod in TODS:
                    pg = await page(b, url, vp={'width': w, 'height': h}, storage=STORE)
                    await pg.evaluate("()=>document.body.classList.add('portraitok')")   # past "Turn your phone sideways"
                    try:
                        await fns[sc](pg, tod)
                        await shot(pg, f'{sc}_{tod}_{w}x{h}.png')
                    except Exception as e:
                        print(f'  {sc} {tod} {w}x{h}: {e}')
                    if pg.errs: print(f'  page errors ({sc} {tod}):', pg.errs[:4])
                    await pg.context.close()
        await b.close()

asyncio.run(main())
