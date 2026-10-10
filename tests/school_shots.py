# School1 item 2 screenshots: the stage map and the placement intake.
# map_<WxH>: stage 1 selected, a student placement with first and pattern passed; map_s3_<WxH>: stage 3 selected (locked);
# intake_<WxH>: the intake with one option picked. At 844x390, 568x320 and 390x844, the intake also at 667x375.
# brief_card1_<WxH>, brief_quiz_<WxH> (item 3): slow flight's briefing, card 1 and the quiz answered wrong.
# hud_cue_<WxH> (item 4): slow flight with the cue strip, ALT out; debrief_<WxH>: a finished slow flight with Easy on.
# item 6: ground_<WxH> (the pylons, the box and the road from the chase view at the start of ground reference),
# landings_aim_<WxH> (short final with the aiming bar), solo_debrief_<WxH> (a passed solo: the Endorsement row), at
# 844x390 and 568x320. item 7: hood_<WxH> (under the hood, the cue strip, at 844x390 and 568x320), xwind_final_844x390
# (crabbed on a one mile final in the lesson's crosswind), emerg_field_844x390 (the forced landing field's outline and
# markers from short final). item 8: logbook_<WxH> (a seeded logbook: 12.5 h, 9.5 dual, 3 solo, 1 instrument, 9 landings, the
# solo endorsement, four entries) at 844x390, 568x320 and 390x844.
# Run: .venv/bin/python tests/school_shots.py   (--item6, --item7, --item8: only those)
import asyncio, os, sys
from playwright.async_api import async_playwright
from harness import serve, launch, page

SHOTS = os.path.join(os.path.dirname(__file__), '..', 'overnight-screenshots', 'school1')
os.makedirs(SHOTS, exist_ok=True)
K = 'window.__kgeu'
BASE = {'kgeuOnboard': 'pilot', 'kgeuTut': '1', 'kgeuCoach': '3', 'kgeuSchool': '{"cessna:first":"A","cessna:pattern":"B"}'}
SIZES = [(844, 390), (568, 320), (390, 844)]

async def shot(pg, name):
    await pg.wait_for_timeout(450)   # past the fades
    p = os.path.abspath(os.path.join(SHOTS, name)); await pg.screenshot(path=p); print(p)

# school1 item 6: the new Stage 1 flights
async def item6(b, url):
    ST = dict(BASE, kgeuPlace='{"level":"ride","hours":null}', kgeuSchoolEasy='0', kgeuTOD='day')
    R = "()=>{const K=window.__kgeu;for(let i=0;i<6;i++)K.stepFrame(0.03,false,false);K.stepFrame(0,true)}"
    for W, H in SIZES[:2]:
        pg = await page(b, url, vp={'width': W, 'height': H}, storage=ST)
        await pg.evaluate(f"()=>{{const K={K};K.startLesson('ground');K.lesBriefSkip();const s=K.state();s.windKt=0;}}")
        await pg.evaluate(R); await shot(pg, f'ground_{W}x{H}.png')
        # short final for runway 1, 200 ft up at 65 kt, the sand bar on the 1,000 ft markers ahead
        await pg.evaluate(f"""()=>{{const K={K},F=K.rwyFrame(),R=F.rh*Math.PI/180,u=F.thr-650;K.startLesson('landings',true,{{brief:false}});const s=K.state();s.windKt=0;
          s.pos.set(Math.sin(R)*u,K.groundHeight(Math.sin(R)*u,-Math.cos(R)*u)+190/3.28084+1.5,-Math.cos(R)*u);const V=33.4;s.vel.set(Math.sin(R)*V,-2.5,-Math.cos(R)*V);
          s.quat.setFromEuler(new THREE.Euler(0.02,-R,0,'YXZ'));s.w.set(0,0,0);s.onGround=false;s.flapIdx=3;s.throttle=s.power=0.35;K.LES.d.s=3;}}""")
        await pg.evaluate(R); await shot(pg, f'landings_aim_{W}x{H}.png')
        # a passed solo: the debrief with the Endorsement row
        await pg.evaluate(f"""()=>{{const K={K};K.startLesson('solo',true,{{brief:false}});if(!K.paused())K.togglePause();K.LES.quiz={{ok:true}};K.gBegin(K.lessonDef('solo'));
          K.gHold('dw',{{get:()=>2110,target:2071,grace:0}});for(let i=0;i<30;i++)K.gTick(0.1);K.gEvent('three',true,'3 of 3');
          K.gRange('fpm',180,'180 fpm, worst of 3, standard 300 fpm');K.gRange('tdz',240,'240 ft past the point, worst of 3, standard 0 to 400 ft');K.gRange('cl',1.8,'1.8 m off, worst of 3, standard 6 m');K.gEnd();}}""")
        await shot(pg, f'solo_debrief_{W}x{H}.png')
        await pg.context.close()

# school1 item 7: the Stage 2 flights
async def item7(b, url):
    ST = dict(BASE, kgeuPlace='{"level":"ride","hours":null}', kgeuSchoolEasy='0', kgeuTOD='day')
    R = "()=>{const K=window.__kgeu;for(let i=0;i<8;i++)K.stepFrame(0.03,false,false);K.stepFrame(0,true)}"
    for W, H in SIZES[:2]:
        pg = await page(b, url, vp={'width': W, 'height': H}, storage=ST)
        await pg.evaluate(f"()=>{{const K={K};K.startLesson('hood');K.lesBriefSkip();const s=K.state();s.windKt=0;s.pos.y+=120/3.28084;}}")
        await pg.evaluate(R); await shot(pg, f'hood_{W}x{H}.png')
        if W == 844:
            # one mile final, crabbed 10 degrees into the lesson's 12 kt crosswind
            await pg.evaluate(f"""()=>{{const K={K};K.startLesson('xwind',true,{{brief:false}});const F=K.rwyFrame(),s=K.state(),sd=K.LES.d.sd,R=F.rh*Math.PI/180,u=F.thr-1852;
              const x=Math.sin(R)*u,z=-Math.cos(R)*u,V=34;s.pos.set(x,K.groundHeight(x,z)+320/3.28084+1.6,z);s.vel.set(Math.sin(R)*V,-1.7,-Math.cos(R)*V);
              s.quat.setFromEuler(new THREE.Euler(0.03,-(R+sd*10*Math.PI/180),0,'YXZ'));s.w.set(0,0,0);s.flapIdx=3;s.throttle=s.power=0.35;}}""")
            await pg.evaluate(R); await shot(pg, f'xwind_final_{W}x{H}.png')
            # the engine failure's field, from 700 m short of it at 250 ft
            await pg.evaluate(f"()=>{{const K={K};K.startLesson('emerg',true,{{brief:false}});const s=K.state();s.windKt=0;s.pos.y-=2500/3.28084;K.LES.ph=2;K.LES.d.t=10;K.stepFrame(0.03,false,true);K.stepFrame(0,true)}}")
            await pg.evaluate(f"""()=>{{const K={K},M=K.lesObjs().filter(o=>o.name==='fieldMk'),s=K.state();const cx=M.reduce((p,o)=>p+o.x,0)/4,cz=M.reduce((p,o)=>p+o.z,0)/4;
              let ax=M[1].x-M[0].x,az=M[1].z-M[0].z;const L=Math.hypot(ax,az);ax/=L;az/=L;const x=cx-ax*1000,z=cz-az*1000,h=Math.atan2(ax,-az),V=33;
              s.pos.set(x,K.groundHeight(x,z)+250/3.28084+1.6,z);s.vel.set(ax*V,-2,az*V);s.quat.setFromEuler(new THREE.Euler(-0.03,-h,0,'YXZ'));s.w.set(0,0,0);}}""")
            await pg.evaluate(R); await shot(pg, f'emerg_field_{W}x{H}.png')
        await pg.context.close()

# school1 item 8: the logbook, seeded
LOGBOOK = {'dual': 9.5, 'solo': 3, 'xc': 0, 'night': 0, 'inst': 1, 'ldg': 9, 'entries': [
    {'id': 'first', 'at': 1791100800000, 'dual': 0.5, 'solo': 0, 'xc': 0, 'night': 0, 'inst': 0, 'ldg': 1, 'score': 92, 'letter': 'A'},
    {'id': 'landings', 'at': 1791360000000, 'dual': 1.0, 'solo': 0, 'xc': 0, 'night': 0, 'inst': 0, 'ldg': 2, 'score': 81, 'letter': 'B'},
    {'id': 'solo', 'at': 1791532800000, 'dual': 0.5, 'solo': 0.5, 'xc': 0, 'night': 0, 'inst': 0, 'ldg': 3, 'score': 88, 'letter': 'B'},
    {'id': 'hood', 'at': 1791619200000, 'dual': 1.0, 'solo': 0, 'xc': 0, 'night': 0, 'inst': 1.0, 'ldg': 0, 'score': 74, 'letter': 'C'}]}

async def item8(b, url):
    import json
    ST = dict(BASE, kgeuPlace='{"level":"solo","hours":35}', kgeuLogbook=json.dumps(LOGBOOK),
              kgeuEndorse='{"solo":{"at":1791532800000,"by":"Dana Reyes, CFI","lesson":"solo"}}')
    for W, H in SIZES:
        pg = await page(b, url, vp={'width': W, 'height': H}, storage=ST)
        await pg.evaluate(f"()=>{{document.body.classList.add('portraitok');{K}.openMenu('sSchool');{K}.nav('sLog')}}")
        await pg.wait_for_timeout(500)
        await shot(pg, f'logbook_{W}x{H}.png')
        await pg.context.close()

async def main():
    srv, url = serve()
    async with async_playwright() as p:
        b = await launch(p)
        if '--item8' in sys.argv:
            await item8(b, url); await b.close(); srv.shutdown(); return
        if '--item7' in sys.argv:
            await item7(b, url); await b.close(); srv.shutdown(); return
        await item6(b, url)
        await item7(b, url)
        await item8(b, url)
        if '--item6' in sys.argv:
            await b.close(); srv.shutdown(); return
        for W, H in SIZES:
            pg = await page(b, url, vp={'width': W, 'height': H}, storage=dict(BASE, kgeuPlace='{"level":"student","hours":12.5}'))
            await pg.evaluate("()=>document.body.classList.add('portraitok')")
            await pg.evaluate(f"()=>{{{K}.openMenu('sSchool');{K}.schSelect('s1')}}")
            await shot(pg, f'map_{W}x{H}.png')
            await pg.evaluate(f"()=>{K}.schSelect('s3')")
            await shot(pg, f'map_s3_{W}x{H}.png')
            await pg.context.close()
        for W, H in SIZES + [(667, 375)]:
            pg = await page(b, url, vp={'width': W, 'height': H}, storage=BASE)
            await pg.evaluate(f"()=>{{document.body.classList.add('portraitok');{K}.openMenu('sSchool')}}"); await pg.wait_for_timeout(300)
            await pg.evaluate("()=>document.querySelector('#plOpts [data-lv=solo]').click()")
            await shot(pg, f'intake_{W}x{H}.png')
            await pg.context.close()
        # school1 item 3: the lesson briefing, card 1 and the quiz with an answer tapped (a wrong one: red, the right one outlined)
        for W, H in SIZES:
            pg = await page(b, url, vp={'width': W, 'height': H}, storage=dict(BASE, kgeuPlace='{"level":"solo","hours":null}'))
            await pg.evaluate(f"()=>{{document.body.classList.add('portraitok');{K}.startLesson('slow')}}")
            await shot(pg, f'brief_card1_{W}x{H}.png')
            for i in range(3): await pg.evaluate(f"()=>{K}.lesBriefNext()"); await pg.wait_for_timeout(400)
            await pg.wait_for_function(f"()=>{{const t=document.getElementById('brTrack');return Math.abs(t.scrollLeft-3*t.clientWidth)<2}}", timeout=8000)
            await pg.evaluate("()=>document.querySelector('#brTrack .brQ .brAns:nth-child(2)').click()")
            await shot(pg, f'brief_quiz_{W}x{H}.png')
            await pg.context.close()
        # school1 item 4: the live cues (250 ft high: ALT out) and the debrief of a finished slow flight flown on Easy
        HOLD = """()=>{const K=window.__kgeu,S=window.__snap;for(let n=0;n<60&&K.LES.on;n++){const s=K.state();s.pos.y=S.y;s.vel.copy(S.v);s.quat.copy(S.q);s.w.set(0,0,0);K.stepFrame(0.1,false,true);}return !!K.LES.on}"""
        for W, H in SIZES:
            pg = await page(b, url, vp={'width': W, 'height': H}, storage=dict(BASE, kgeuPlace='{"level":"solo","hours":null}', kgeuSchoolEasy='1'))
            await pg.evaluate(f"()=>{{document.body.classList.add('portraitok');{K}.startLesson('slow');{K}.lesBriefAnswer(0);{K}.lesBriefSkip()}}")
            await pg.evaluate(f"()=>{{const K={K};for(let n=0;n<400&&K.LES.ph!==1;n++)K.stepFrame(0.1,false,true);K.stepFrame(0,true)}}")
            await pg.evaluate(f"()=>{{const s={K}.state();window.__snap={{y:s.pos.y,v:s.vel.clone(),q:s.quat.clone()}};s.pos.y+=500/3.28084}}")
            await pg.evaluate(f"()=>{K}.ff(0.5)"); await pg.wait_for_timeout(600)
            await shot(pg, f'hud_cue_{W}x{H}.png')
            for _ in range(12):
                if not await pg.evaluate(HOLD): break
            await pg.evaluate(f"()=>{K}.stepFrame(0,true)")
            await shot(pg, f'debrief_{W}x{H}.png')
            await pg.context.close()
        await b.close()
    srv.shutdown()
asyncio.run(main())
