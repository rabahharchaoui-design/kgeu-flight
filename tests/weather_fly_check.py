# Weather item 4: how each weather flies and what the tower says about it.
# With windSeed(7), for every weather type: the Cessna on the runway at Glendale, wxFly() read back.
#  - the wind and gust inside WX_SET's ranges (Hard), Easy at 0.6 of the knots and half the gust (never under clear's)
#  - the gusty winds 40 to 70 degrees off runway 1 (a 10 to 20 kt crosswind), Easy 20 to 30
#  - turbulence: non zero in the gusty winds below 300 m, zero in clear air; the storm's near a cell; a gust front surges
#  - the wet runway: a scripted ground roll from 60 kt with the brakes stops in at least 1.4x the clear distance in rain
#  - the ATIS readout names the right visibility and sky per type, before the takeoff clearance, and every clip of it is
#    in radio/clips.json
# Run: .venv/bin/python tests/weather_fly_check.py
import asyncio, json, os, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page, Checks, IPHONE_15, ROOT
ok = Checks()
K = 'window.__kgeu'
CLIPS = set(json.load(open(os.path.join(ROOT, 'radio', 'clips.json'))))
RANGE = {'clear': (2, 6, 0.1), 'scattered': (4, 9, 0.2), 'overcast': (5, 10, 0.15), 'rain': (8, 14, 0.3),
         'storm': (10, 16, 0.6), 'fog': (0, 3, 0.05), 'gusty': (18, 24, 0.55)}
VIS = {'clear': 'visibility 10 miles', 'scattered': 'visibility 10 miles', 'overcast': 'visibility 10 miles',
       'rain': 'visibility 3 miles in rain', 'storm': 'visibility 5 miles', 'fog': 'visibility one mile in fog',
       'gusty': 'visibility 10 miles', 'haboob': 'visibility 10 miles'}
SKY = {'clear': 'sky clear', 'scattered': 'few clouds at', 'overcast': ' overcast', 'rain': ' overcast',
       'storm': 'thunderstorms in the vicinity', 'fog': ' overcast', 'gusty': 'few clouds at', 'haboob': 'blowing dust'}

START = """([wx,skill])=>{const K=window.__kgeu;K.setSkill(skill);K.setTOD('day');K.setWX(wx);K.windSeed(7);
  K.pick('cessna');K.pickBase('kgeu');K.pickPos('runway');K.radioLog(true);K.start('runway');
  for(let i=0;i<30;i++)K.stepFrame(1/60,false,true);
  const s=K.state();return Object.assign(K.wxFly(),{base:s.windBase,atis:K.atis(),log:K.radioLog().map(l=>({text:l.text,clips:l.clips,who:l.who}))});}"""

# a ground roll from 60 kt along runway 1, throttle closed, brakes on: the distance to a stop (m)
ROLL = """([wx])=>{const K=window.__kgeu;K.setSkill('pilot');K.setWX(wx);K.windSeed(7);K.pick('cessna');K.pickBase('kgeu');K.start('runway');
  for(let i=0;i<10;i++)K.stepFrame(1/60,false,true);
  const s=K.state(),h=K.BASES.kgeu.hdg*Math.PI/180,V=60*0.5144;s.vel.set(Math.sin(h)*V,0,-Math.cos(h)*V);s.throttle=s.power=0;s.brake=true;
  const x0=s.pos.x,z0=s.pos.z;let n=0;K.touchIn.brake=true;   // the brake held the way the BRAKE button holds it
  while(Math.hypot(s.vel.x,s.vel.z)>0.5&&n<3000){s.throttle=0;K.stepFrame(1/60,false,true);n++;}
  K.touchIn.brake=false;
  return {d:Math.hypot(s.pos.x-x0,s.pos.z-z0),wet:s.wet,crashed:s.crashed,n:n};}"""

# airborne at h m above the ground near the field, for the turbulence by height
AIR = """([h])=>{const K=window.__kgeu,s=K.state();s.pos.y=K.groundHeight(s.pos.x,s.pos.z)+h;s.onGround=false;
  const hd=K.BASES.kgeu.hdg*Math.PI/180,V=55;s.vel.set(Math.sin(hd)*V,0,-Math.cos(hd)*V);s.throttle=s.power=0.7;s.flapIdx=0;
  let mx=0;for(let i=0;i<240;i++){s.pos.y=K.groundHeight(s.pos.x,s.pos.z)+h;s.vel.y=0;K.stepFrame(1/60,false,true);mx=Math.max(mx,s.turb);}
  return {turb:s.turb,mx:mx,agl:s.agl,crashed:s.crashed};}"""


async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        pg = await page(b, url, vp=IPHONE_15, storage={'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3'})
        await pg.evaluate(f"()=>{K}.initAudio()")
        hard = {}
        for wx in list(RANGE) + ['haboob']:
            r = await pg.evaluate(START, [wx, 'pilot'])
            hard[wx] = r
            a = r['atis'] or ''
            print(f"  {wx:9s} wind {r['windDir']:.0f}/{r['windKt']:.1f} G{r['gustKt']} gust {r['gustAmp']:.2f} turb {r['turb']:.2f} wet {r['wet']} vis {r['vis']} ceil {r['ceil']} alt {r['altim']}")
            print(f"            {a}")
            if wx in RANGE:
                k0, k1, g = RANGE[wx]
                ok(f'{wx}: wind {k0} to {k1} kt, gust {g}', k0 <= r['windKt'] <= k1 + 0.5 and abs(r['gustAmp'] - g) < 1e-6 and r['wxW'] == 1, (r['windKt'], r['gustAmp']))
            else:
                ok('haboob: the wall\'s own 8 kt and gust 0.35 (hbUpdate keeps it)', round(r['windKt']) == 8 and abs(r['gustAmp'] - 0.35) < 1e-6 and r['wxW'] == 0, (r['windKt'], r['gustAmp']))
            ok(f'{wx}: ATIS names "{VIS[wx]}" and "{SKY[wx].strip()}"', VIS[wx] + ',' in a and SKY[wx] in a and ' information ' in a and 'altimeter ' in a, a)
            al = r['altim']
            ok(f'{wx}: altimeter 29.85 to 30.15', 29.85 <= al <= 30.15, al)
            log = r['log']
            first = log[0] if log else None
            ok(f'{wx}: the ATIS is the first line, before any clearance', first and ' information ' in first['text'] and not any('cleared' in l['text'] for l in log), [l['text'][:60] for l in log])
            if first:
                miss = [c for c in first['clips'] if c not in CLIPS]
                ok(f'{wx}: every ATIS clip is recorded ({len(first["clips"])} clips)', not miss, miss)
        gy = hard['gusty']
        off = abs(((gy['base'] - 26) + 180) % 360 - 180)
        ok('gusty: the wind 40 to 70 degrees off runway 1 (10 to 20 kt crosswind)', 35 <= off <= 75, (gy['base'], off))
        ok('gusty: the ATIS says gusting', ' gusting ' in gy['atis'], gy['atis'])
        hud = await pg.evaluate("()=>document.getElementById('hWindT').textContent")
        # Easy
        for wx in ('gusty', 'rain', 'clear', 'fog'):
            e = await pg.evaluate(START, [wx, 'rookie'])
            h = hard[wx]
            k0, k1, g = RANGE[wx]
            wk = max(h['windKt'] * 0.6, min(h['windKt'], 2))
            ok(f'Easy {wx}: 0.6 of the knots, half the gust (never under clear\'s)', abs(e['windKt'] - round(wk)) <= 1 and abs(e['gustAmp'] - max(g * 0.5, min(g, 0.1))) < 1e-6, (h['windKt'], e['windKt'], e['gustAmp']))
            if wx == 'gusty':
                eo = abs(((e['base'] - 26) + 180) % 360 - 180)
                ok('Easy gusty: 20 to 30 degrees off runway 1 (the autoland\'s crosswind)', 15 <= eo <= 35, (e['base'], eo))
                plain = await pg.evaluate("()=>{const e=document.querySelector('#atc .plain');return e?e.textContent:''}")
                ok('Easy: the ATIS has its plain line', plain.startswith('Weather: wind from the'), plain)
        # turbulence
        await pg.evaluate(START, ['gusty', 'pilot'])
        t = await pg.evaluate(AIR, [200])
        ok('gusty, 200 m AGL: turbulence over 0.4', t['mx'] > 0.4 and not t['crashed'], t)
        await pg.evaluate(START, ['gusty', 'rookie'])
        t2 = await pg.evaluate(AIR, [200])
        ok('Easy gusty, 200 m AGL: 0.4 of it', t2['mx'] < 0.3 and t2['mx'] > 0.1, t2)
        await pg.evaluate(START, ['clear', 'pilot'])
        t = await pg.evaluate(AIR, [200])
        ok('clear, 200 m AGL: no turbulence', t['mx'] == 0, t)
        # the storm: near a cell, a front
        await pg.evaluate(START, ['storm', 'pilot'])
        s = await pg.evaluate("""()=>{const K=window.__kgeu,s=K.state(),c=K.wxCell(s.pos.x,s.pos.z);if(!c)return null;
          s.pos.set(c.x+1500,K.groundHeight(c.x+1500,c.z)+600,c.z);s.onGround=false;s.vel.set(0,0,-55);s.flapIdx=0;s.throttle=s.power=0.7;
          let mx=0;for(let i=0;i<180;i++){s.vel.y=0;K.stepFrame(1/60,false,true);mx=Math.max(mx,s.turb);}
          const kt0=s.windKt;K.wxFront();for(let i=0;i<420;i++){s.vel.y=0;K.stepFrame(1/60,false,true);}
          const f=K.wxFly();return {mx:mx,kt0:kt0,kt:s.windKt,front:f.front,hud:document.getElementById('hWindT').textContent};}""")
        ok('storm: 1.5 km from a cell, turbulence toward 0.8', s and s['mx'] > 0.6, s)
        ok('storm: a gust front adds 15 to 25 kt (7 s in)', s and s['front']['on'] and 14 <= s['kt'] - s['kt0'] <= 26, s)
        # braking
        dry = await pg.evaluate(ROLL, ['clear'])
        wet = await pg.evaluate(ROLL, ['rain'])
        ok('rain: the runway is wet, clear dry', wet['wet'] == 1 and dry['wet'] == 0, (dry, wet))
        ok('rain: stopping from 60 kt takes at least 1.4x the clear distance', wet['d'] >= 1.4 * dry['d'] and not wet['crashed'], (round(dry['d']), round(wet['d'])))
        ok('no page errors', not pg.errs, pg.errs[:3])
        await b.close()
    srv.shutdown()
    sys.exit(ok.done('weather_fly_check'))

asyncio.run(main())
