# Runways item 7: every flyable aircraft at true scale, lined up on its base runway next to the
# centreline and threshold marks (chase view) and on the ramp beside the hangars and stands, so
# the scale reads at a glance; one combined sheet for the report.
#   .venv/bin/python tests/scale_shots.py [out_dir]     (default overnight-screenshots/runways_scale)
import asyncio, os, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, IPHONE_15
from PIL import Image, ImageDraw, ImageFont

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), '..', 'overnight-screenshots', 'runways_scale')
STORAGE = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'}
# the base with the right runway for the type (the airliners need 2,400 m: Sky Harbor)
BASE = {'cessna': 'kgeu', 'archer': 'kgeu', 'alpha': 'kgeu', 'reaper': 'kgeu', 'mq9b': 'kgeu',
        'f16': 'luke', 'a10': 'luke', 'c130': 'luke', 'b737': 'phx', 'a320': 'phx', 'b747': 'phx'}
CAM_JS = "(m)=>{const K=window.__kgeu;let k=0;while(K.camMode()!==m&&k++<6)K.cycleCam();}"
START_JS = "([t,b,mode])=>{const K=window.__kgeu;K.setTOD('day');if(K.setWX){try{K.setWX('clear');}catch(e){}}K.pick(t);K.pickBase(b);K.start(mode);}"
SNAP_JS = "()=>{const K=window.__kgeu;K.snapCam();for(let i=0;i<6;i++)K.stepFrame(1/30);}"
HIDE_JS = "(on)=>{document.body.classList.toggle('shotclean',on);const h=document.getElementById('hud');if(h)h.style.visibility=on?'hidden':'';}"

async def main():
    os.makedirs(OUT, exist_ok=True)
    srv, url = serve()
    shots = []
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage=STORAGE)
        for t, base in BASE.items():
            for mode in ('runway', 'ramp'):
                await pg.evaluate(START_JS, [t, base, mode])
                await pg.wait_for_timeout(1200)
                await pg.evaluate(CAM_JS, 0)
                await pg.evaluate(SNAP_JS)
                await pg.wait_for_timeout(200)
                path = os.path.join(OUT, f'{t}_{mode}.png')
                await pg.screenshot(path=path)
                shots.append((t, mode, path))
                print(' ', path)
        print('errors:', pg.errs[:5])
        await b.close()
    srv.shutdown()
    # the sheet: a row per aircraft, runway then ramp, half size
    W, H = 422, 195
    try: font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 13)
    except Exception: font = ImageFont.load_default()
    types = list(BASE)
    sheet = Image.new('RGB', (2 * W + 10, len(types) * (H + 18) + 10), (20, 20, 24))
    d = ImageDraw.Draw(sheet)
    for i, t in enumerate(types):
        for j, mode in enumerate(('runway', 'ramp')):
            path = os.path.join(OUT, f'{t}_{mode}.png')
            if not os.path.exists(path): continue
            im = Image.open(path).convert('RGB').resize((W, H))
            x, y = 5 + j * (W + 5), 5 + i * (H + 18)
            sheet.paste(im, (x, y + 16))
            d.text((x + 4, y + 1), f'{t}  {mode}  ({BASE[t]})', fill=(240, 240, 240), font=font)
    sp = os.path.join(OUT, 'scale_sheet.png'); sheet.save(sp); print('sheet', sp, sheet.size)

asyncio.run(main())
