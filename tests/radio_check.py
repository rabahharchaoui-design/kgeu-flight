# ATC radio: clips load, lines stitch, the radio chain is in place, controls work.
import asyncio, os, sys, json, threading, functools, http.server, socketserver
from playwright.async_api import async_playwright

def serve(root):
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=root)
    class Q(socketserver.TCPServer): allow_reuse_address = True
    srv = Q(('127.0.0.1', 0), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f'http://127.0.0.1:{srv.server_address[1]}/index.html'

THREE=open('node_modules/three/build/three.min.js').read()
SRV,URL=serve(os.path.abspath('.'))
SHOTS=os.path.abspath('overnight-screenshots')
fails=[]
def chk(n,c,d=''):
    print(('  ok   ' if c else '  FAIL ')+n+(('  '+d) if d else ''))
    if not c: fails.append(n)

async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(args=['--use-gl=swiftshader','--enable-unsafe-swiftshader',
                                    '--autoplay-policy=no-user-gesture-required'])
    pg=await (await b.new_context(viewport={'width':844,'height':390},is_mobile=True,has_touch=True)).new_page()
    errs=[]
    pg.on('pageerror',lambda e:errs.append(str(e)))
    await pg.route('**/three.min.js',lambda r:r.fulfill(body=THREE,content_type='application/javascript'))
    await pg.route('**/fonts.googleapis.com/**',lambda r:r.abort())
    await pg.goto(URL); await pg.wait_for_timeout(2000)

    manifest=json.load(open('radio/clips.json'))
    chk('clip manifest is on disk', len(manifest)>80, f'{len(manifest)} clips')
    missing=[c for c in manifest if not os.path.exists(f'radio/{c}.m4a')]
    chk('every manifest clip has a file', not missing, str(missing[:3]))

    await pg.evaluate("()=>window.__kgeu.initAudio()")
    # loading is six at a time over localhost; give it room
    for _ in range(40):
        st=await pg.evaluate("()=>{const R=window.__kgeu.RADIO;return {want:R.want,got:R.got,err:R.err};}")
        if st['want'] and st['got']+max(0,st['err'])>=st['want']: break
        await pg.wait_for_timeout(500)
    chk('clips decode in the browser', st['got']>=len(manifest)-2, json.dumps(st))
    chk('no decode failures', st['err']<=0 or st['err']==0, f"err {st['err']}")

    # Render noise through the real chain offline and measure where the energy went.
    # This is the only way to prove the radio filter is actually applied.
    spec=await pg.evaluate("""async()=>{
      const K=window.__kgeu, SR=48000, N=SR;            // one second
      const off=new OfflineAudioContext(1,N,SR);
      const b=off.createBuffer(1,N,SR),d=b.getChannelData(0);
      for(let i=0;i<N;i++)d[i]=(Math.random()*2-1)*0.25;
      const c=K.radioChain(off,1.0);
      const s=off.createBufferSource();s.buffer=b;s.connect(c.inp);s.start(0);
      const r=await off.startRendering();
      const x=r.getChannelData(0);
      // Goertzel at a few probe frequencies: cheap and exact enough for a band check
      const mag=f=>{const w=2*Math.PI*f/SR,cw=2*Math.cos(w);let s1=0,s2=0;
        for(let i=0;i<N;i++){const t=x[i]+cw*s1-s2;s2=s1;s1=t;}
        return Math.sqrt(s1*s1+s2*s2-cw*s1*s2)/N;};
      const out={};
      for(const f of [60,120,300,800,1500,3000,6000,12000]) out[f]=mag(f);
      return out;}""")
    band = spec['1500']
    chk('passband (1.5 kHz) carries the signal', band > 1e-5, f"{band:.2e}")
    chk('below 300 Hz is rolled off', spec['60'] < band*0.25, f"60 Hz {spec['60']/band:.3f} of passband")
    chk('120 Hz is rolled off', spec['120'] < band*0.5, f"120 Hz {spec['120']/band:.3f} of passband")
    chk('above 3 kHz is rolled off', spec['6000'] < band*0.5, f"6 kHz {spec['6000']/band:.3f} of passband")
    chk('12 kHz is well gone', spec['12000'] < band*0.15, f"12 kHz {spec['12000']/band:.3f} of passband")
    chk('800 Hz and 1.5 kHz are both in the passband', spec['800'] > band*0.4, f"800 Hz {spec['800']/band:.3f}")
    # a real line: takeoff clearance for the C-130 at Luke
    await pg.evaluate("()=>{window.__kgeu.pick('c130');window.__kgeu.pickBase('luke');window.__kgeu.start('runway');}")
    await pg.wait_for_timeout(2500)
    line=await pg.evaluate("()=>{const e=document.getElementById('atc');return {on:e.classList.contains('on'),txt:e.textContent};}")
    chk('takeoff clearance is transmitted', line['on'] and 'cleared for takeoff' in line['txt'], repr(line['txt'][:110]))
    chk('it names the right tower and runway', 'Luke Tower' in line['txt'] and '03L' in line['txt'], repr(line['txt'][:110]))
    chk('it uses the C-130 callsign', 'Herky 71' in line['txt'], repr(line['txt'][:60]))
    await pg.screenshot(path=f'{SHOTS}/radio_takeoff.png')

    # The pilot reads it back in the other voice. Assert on the queue rather than
    # waiting: the main loop clamps dt to 0.1 s, so at the 3 fps this harness gets
    # the radio clock runs at roughly a third of real time.
    q=await pg.evaluate("()=>window.__kgeu.radioQ().map(l=>({who:l.who,text:l.text,clips:l.clips}))")
    rb=[l for l in q if 'Cleared for takeoff' in l['text']]
    chk('the pilot reads the clearance back', bool(rb), json.dumps(q[:2]))
    if rb:
        chk('the readback is in the pilot voice', all(c.startswith('p_') for c in rb[0]['clips']),
            json.dumps(rb[0]['clips']))
        chk('the readback names the aircraft', 'Herky 71' in rb[0]['text'], rb[0]['text'])

    # stitching: a line made of many clips takes proportionally longer
    d=await pg.evaluate("""()=>{const K=window.__kgeu;
      const one=K.radioSpeak(['t_cleared_to'],20);
      const many=K.radioSpeak(['t_cs_herky','t_luke_tower','t_wind','t_n_0','t_n_6','t_n_0','t_at','t_n_9','t_rwy_03l','t_cleared_to'],80);
      return {one:one,many:many};}""")
    chk('a stitched line is longer than a single clip', d['many']>d['one']*2, json.dumps({k:round(v,2) for k,v in d.items()}))

    # controls
    await pg.evaluate("()=>window.__kgeu.setRadioVol(0.3)")
    v=await pg.evaluate("()=>window.__kgeu.RADIO.vol")
    chk('volume slider sets the level', abs(v-0.3)<0.01, str(v))
    await pg.evaluate("()=>window.__kgeu.setRadioOn(false)")
    off=await pg.evaluate("()=>window.__kgeu.RADIO.on")
    chk('radio can be muted', off==False, str(off))
    await pg.evaluate("()=>window.__kgeu.setRadioOn(true)")
    await pg.evaluate("()=>window.__kgeu.openMenu()")
    await pg.wait_for_timeout(500)
    chk('controls are in the menu', await pg.is_visible('#oRadio') and await pg.is_visible('#oRvol'))
    await pg.screenshot(path=f'{SHOTS}/radio_menu.png')

    chk('no console errors', not errs, ' | '.join(errs[:2]))
    await b.close()
  print(f'FAILS {len(fails)}'+((': '+'; '.join(fails)) if fails else ''))
  sys.exit(1 if fails else 0)
asyncio.run(main())
