# Renders icons/share-card.png (1200x630) for link previews: the app icon on sand
# with the title. Run: .venv/bin/python tools/make_share_card.py
import asyncio, os, base64
from playwright.async_api import async_playwright
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
icon = base64.b64encode(open(os.path.join(ROOT, 'icons/icon-1024.png'), 'rb').read()).decode()
HTML = f"""<html><body style="margin:0;width:1200px;height:630px;background:linear-gradient(180deg,#F6C177 0%,#F6C177 74%,#D98A3D 74%,#D98A3D 84%,#A8592A 84%,#A8592A 93%,#6B3517 93%);
display:flex;align-items:center;gap:56px;padding:0 90px 60px;box-sizing:border-box;font-family:'Arial Narrow','Helvetica Neue',sans-serif">
<img src="data:image/png;base64,{icon}" style="width:340px;height:340px;border-radius:76px;box-shadow:0 18px 40px rgba(42,22,8,.35)">
<div><div style="font-size:112px;font-weight:900;color:#2A1608;letter-spacing:-2px;line-height:.95">Pocket<br>Flight Sim</div>
<div style="font-size:38px;font-weight:700;color:#2A1608;opacity:.8;margin-top:18px">Fly the Arizona desert.<br>F-16, Reaper, C-130, Cessna.</div></div></body></html>"""
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={'width': 1200, 'height': 630})
        await pg.set_content(HTML); await pg.screenshot(path=os.path.join(ROOT, 'icons/share-card.png')); await b.close()
asyncio.run(main())
