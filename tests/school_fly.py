# School1 item 6: shared helpers for the lesson flight checks (school_climbs_check, school_ground_check,
# school_landings_check, school_solo_check). The lesson clock runs on the frame time, so the plane is pinned frame by frame:
# FLY sets the speed (kt, indicated), the vertical speed (fpm), the heading, the bank, optionally a new altitude (MSL ft,
# once) or position (x, z, once), then steps one 0.1 s frame without rendering, until n frames or the until test is true.
K = 'window.__kgeu'
BASE = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3', 'kgeuSchoolEasy': '0', 'kgeuTOD': 'day'}
FLY = """([n,o])=>{const K=window.__kgeu,u=o.until?new Function('K','s','return '+o.until):null;let i=0;
  for(;i<n&&K.LES.on;i++){const s=K.state();s.windKt=0;s.gustAmp=0;
    if(o.alt!=null){s.pos.y+=(o.alt-K.G.alt)/3.28084;o.alt=null;}
    if(o.x!=null){s.pos.x=o.x;s.pos.z=o.z;o.x=null;}
    if(o.agl!=null){s.pos.y=K.groundHeight(s.pos.x,s.pos.z)+o.agl/3.28084+(o.gear||1.3);o.agl=null;}
    if(o.thr!=null){s.throttle=s.power=o.thr;}
    const hd=o.hdg+(o.rate||0)*i*0.1,h=hd*Math.PI/180,V=o.kt/1.943844/Math.sqrt(1.097*Math.exp(-s.pos.y/9200)/1.225),vy=(o.vs||0)/196.85;
    s.vel.set(Math.sin(h)*V,vy,-Math.cos(h)*V);s.quat.setFromEuler(new THREE.Euler(Math.atan2(vy,V)+0.04,-h,-(o.bank||0)*Math.PI/180,'YXZ'));s.w.set(0,0,0);
    s.onGround=false;K.stepFrame(0.1,false,true);if(u&&u(K,K.state()))break;}
  K.stepFrame(0,true);const L=K.LES;return {i:i,ph:L.ph,on:L.on,alt:Math.round(K.G.alt),kt:Math.round(K.G.kt),d:{s:L.d.s,c:L.d.c,k:L.d.k,n:L.d.n}}}"""
STEP = "(n)=>{const K=window.__kgeu;for(let i=0;i<n&&K.LES.on;i++)K.stepFrame(0.1,false,true);K.stepFrame(0,true)}"
DEBRIEF = """()=>({on:document.getElementById('gradeOv').classList.contains('on'),letter:document.getElementById('gLetter').textContent,
  rows:[...document.querySelectorAll('#gLines .gt')].map(r=>[r.querySelector('span').textContent,r.classList.contains('ok'),r.querySelector('b').textContent]),
  why:[...document.querySelectorAll('#gLines .no:not(.gt)')].map(r=>r.textContent),
  gl:[...document.querySelectorAll('#gLines .gl')].map(r=>[r.querySelector('span').textContent,r.querySelector('b').textContent]),
  res:window.__kgeu.G.res&&{score:window.__kgeu.G.res.score,lines:window.__kgeu.G.res.lines.map(l=>[l.name,l.ok,l.detail])}})"""
DANA = "()=>window.__kgeu.radioLog().filter(l=>l.who==='Dana').map(l=>l.text)"

async def start(pg, lid):
    await pg.evaluate(f"(id)=>{{const K={K};K.radioLog(true);K.startLesson(id);K.lesBriefSkip();const s=K.state();s.windKt=0;s.gustAmp=0;}}", lid)
    await pg.wait_for_timeout(200)

async def fly(pg, n, **o):
    return await pg.evaluate(FLY, [n, o])

def said(lines, *words):
    """every word (a regex-free substring) is in some line Dana said"""
    return [w for w in words if not any(w in l for l in lines)]

# ---- the circuits (school_landings_check, school_solo_check): positions on runway 1's frame (u along it from its start,
# v to the right), the steps of LES.d.s: 0 takeoff and climb, 1 crosswind, 2 downwind, 3 base and final, 4 on the runway
UV = "(u,v)=>{const K=window.__kgeu,R=K.rwyFrame().rh*Math.PI/180;return [Math.sin(R)*u+Math.cos(R)*v,-Math.cos(R)*u+Math.sin(R)*v]}"

async def rwy(pg):
    return await pg.evaluate(f"()=>{K}.rwyFrame()")

async def xz(pg, u, v):
    return await pg.evaluate(f"([u,v])=>({UV})(u,v)", [u, v])

async def call(pg, n=400):
    """step until the CALL button is up, tap it (tqAnswer); True if it was there"""
    r = await pg.evaluate(f"(n)=>{{const K={K};for(let i=0;i<n&&K.LES.on;i++){{if(K.TASK.ask&&K.TASK.ask.shown)break;K.stepFrame(0.1,false,true);}}K.stepFrame(0,true);return !!(K.TASK.ask&&K.TASK.ask.shown)}}", n)
    if r: r = await pg.evaluate(f"()=>{K}.tqAnswer('CALL')")
    return r

async def climbout(pg, F):
    x, z = await xz(pg, F['thr'] + 1300, 0)
    return await fly(pg, 40, x=x, z=z, agl=760, kt=74, vs=600, hdg=F['rh'], until="K.LES.d.s===1")

async def downwind(pg, F, n=60):
    x, z = await xz(pg, F['thr'] + 1500, 900)
    return await fly(pg, n, x=x, z=z, agl=2100 - F['field'], kt=95, vs=0, hdg=F['rh'] + 180)

async def base(pg, F):
    x, z = await xz(pg, F['thr'] + 100, 900)
    return await fly(pg, 20, x=x, z=z, agl=1000, kt=80, vs=-400, hdg=F['rh'] - 90, until="K.LES.d.s===3")

async def final(pg, F, kt=65, to=60):
    x, z = await xz(pg, F['thr'] - 1300, 0)
    await fly(pg, 60, x=x, z=z, agl=390, kt=kt, vs=-500, hdg=F['rh'])
    return await fly(pg, 30, agl=to, kt=kt, vs=-300, hdg=F['rh'])

async def touchdown(pg, F, past=60, fpm=150, v=1.0):
    """a touchdown event `past` metres past the aiming bar (the physics would take minutes), the plane held off the ground"""
    x, z = await xz(pg, F['thr'] + F['aim'] + past, v)
    await pg.evaluate(f"([x,z,f])=>{{const K={K};K.events.push({{type:'touchdown',fpm:f,paved:K.isPaved(x,z),x:x,z:z,ias:33,bank:0}})}}", [x, z, fpm])
    return await fly(pg, 2, agl=30, kt=60, vs=-100, hdg=F['rh'])

async def stop(pg, F, u=700, n=30):
    """stopped on the runway: on the pavement, wheels on the ground, no speed"""
    x, z = await xz(pg, F['thr'] + u, 0)
    return await pg.evaluate(f"""([x,z,n])=>{{const K={K};for(let i=0;i<n&&K.LES.on;i++){{const s=K.state();s.pos.set(x,K.groundHeight(x,z)+K.rwyFrame().gear,z);s.vel.set(0,0,0);s.w.set(0,0,0);s.onGround=true;s.throttle=0;K.stepFrame(0.1,false,true);}}
      K.stepFrame(0,true);return {{on:K.LES.on,ph:K.LES.ph,s:K.LES.d.s,c:K.LES.d.c}}}}""", [x, z, n])
