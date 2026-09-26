# Playwright visual check. Run from project root: python3 tests/ui_check.py
import asyncio,os
from playwright.async_api import async_playwright
THREE=open('node_modules/three/build/three.min.js').read()
URL='file://'+os.path.abspath('index.html')
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(args=['--use-gl=swiftshader','--enable-webgl','--ignore-gpu-blocklist','--enable-unsafe-swiftshader'])
    for w,h in [(844,390),(932,430),(667,375)]:
      ctx=await b.new_context(viewport={'width':w,'height':h},has_touch=True,is_mobile=True,device_scale_factor=2)
      pg=await ctx.new_page();errs=[];pg.on('pageerror',lambda e: errs.append(str(e)))
      await pg.route('**/three.min.js',lambda r: r.fulfill(body=THREE,content_type='application/javascript'))
      await pg.route('**/fonts.googleapis.com/**',lambda r: r.abort())
      await pg.goto(URL);await pg.wait_for_timeout(2500)
      await pg.tap('#bRunway');await pg.wait_for_timeout(1500)
      await pg.screenshot(path=f'tests/shot_{w}x{h}.png')
      print(w,h,'errors:',errs)
      await ctx.close()
    await b.close()
asyncio.run(main())
