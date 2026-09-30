// Easy hands-off landing matrix (phone item 12). Every aircraft, every runway end at Glendale and
// Luke, from the 3 nm and the 1 nm final, in calm air and three seeded winds (10 kt crosswind from
// the left, from the right, and a quartering tailwind, all with the game's normal gusts). The stick
// is never touched. Runs the real physics block at 120 Hz with the phone's 60 fps frame cadence.
// A landing is clean when: no crash; the mains touch on the runway inside the touchdown zone
// (threshold to 914 m past it); under 300 fpm; no bounce; within 3 m of the centreline at touchdown
// and 4 m all the rollout; it stops on the runway.
// Run: node tests/easy_land.js [types=cessna,f16] [ends=1,19] [finals=3,1] [winds=calm,L,R,T] [v]
const THREE=require('three');global.THREE=THREE;
const fs=require('fs');const src=fs.readFileSync(process.env.F||__dirname+'/../index.html','utf8');
const phys=src.split('// PHYSICS-START')[1].split('// PHYSICS-END')[0];
const api=new Function('THREE',phys+`
return {createState,step,setType,autopilot,trimSpawn,groundHeight,isPaved,TYPES,GS,KT,
  windSeed:typeof windSeed==='function'?windSeed:null,
  ends:()=>{const out=[],H=26*Math.PI/180;
    const add=(apt,num,x,z,h,len,thr)=>out.push({apt,num,x,z,h,len,thr});
    // pavement from -thr to len-thr along the landing direction, measured from the threshold
    const d=[Math.sin(H),-Math.cos(H)],c=[wX(RWY_LEN/2,0),wZ(RWY_LEN/2,0)];
    add('KGEU','1',c[0]-d[0]*(RWY_LEN/2-THR01),c[1]-d[1]*(RWY_LEN/2-THR01),H,RWY_LEN,THR01);
    add('KGEU','19',c[0]+d[0]*(RWY_LEN/2-(RWY_LEN-THR19)),c[1]+d[1]*(RWY_LEN/2-(RWY_LEN-THR19)),H+Math.PI,RWY_LEN,RWY_LEN-THR19);
    const L=42.6*Math.PI/180,ld=[Math.sin(L),-Math.cos(L)];
    for(const r of LUKE_RWY){const cx=lkX(0,r.v),cz=lkZ(0,r.v);
      add('KLUF',r.lo,cx-ld[0]*r.len/2,cz-ld[1]*r.len/2,L,r.len,0);
      add('KLUF',r.hi,cx+ld[0]*r.len/2,cz+ld[1]*r.len/2,L+Math.PI,r.len,0);}
    return out;}};`)(THREE);
const arg=k=>{const a=process.argv.find(s=>s.startsWith(k+'='));return a?a.split('=')[1].split(','):null;};
const TYPES=arg('types')||['cessna','alpha','reaper','mq9b','f16','c130'];
const ENDS=api.ends().map((e,i)=>Object.assign(e,{idx:i})).filter(e=>!arg('ends')||arg('ends').includes(e.num));
const FINALS=(arg('finals')||['3','1']).map(Number);
const WINDS=(arg('winds')||['calm','L','R','T']).concat(arg('rand')?[...Array(+arg('rand')[0]).keys()].map(i=>'r'+(i+1)):[]);
const VERB=process.argv.includes('v');
// seeded RNG for the gusts: the game's hook when it has one, else Math.random itself
function mulberry(a){return ()=>{a=(a+0x6D2B79F5)>>>0;let t=a;t=Math.imul(t^(t>>>15),t|1);t^=t+Math.imul(t^(t>>>7),t|61);return ((t^(t>>>14))>>>0)/4294967296;};}
const RND0=Math.random;
function seed(s){if(api.windSeed)api.windSeed(s);else Math.random=mulberry(s);}
const wrap=a=>Math.atan2(Math.sin(a),Math.cos(a));
// wind relative to the landing direction: from 90 deg left, 90 deg right, 135 deg right (tail quartering)
const WREL={L:-90,R:90,T:135};

function fly(type,E,nm,wind,ei){
  api.setType(type);
  seed(1000+(ei||0)*100+nm*10+(wind==='calm'?0:String(wind).charCodeAt(0))+(+String(wind).slice(1)||0)*1000);
  const D=nm===1?1852:5556,tg=Math.tan(api.GS);
  const st=api.createState('final','kgeu',nm===1?1852:0);
  // move the spawn onto this runway end: D before the aim point (300 m past the threshold), on the path
  const dx=Math.sin(E.h),dz=-Math.cos(E.h),back=D-300,gh=api.groundHeight(E.x-dx*back,E.z-dz*back);
  const V=st.vel.length();
  st.pos.set(E.x-dx*back,gh+D*tg+1.5,E.z-dz*back);st.vel.set(dx*V*Math.cos(api.GS),-V*Math.sin(api.GS),dz*V*Math.cos(api.GS));
  st.quat.setFromEuler(new THREE.Euler(0,-E.h,0,'YXZ'));
  if(wind==='calm'){st.windKt=0;st.windBase=st.windDir=0;st.gustAmp=0;}
  else if(WREL[wind]!==undefined){const wd=((E.h*180/Math.PI+WREL[wind])%360+360)%360;st.windBase=st.windDir=wd;st.windKt=10;st.windPh=0;}
  // 'r<n>': the game's own random wind (1 to 10 kt, any direction) from seed n, as createState draws it
  else{const r=mulberry(+wind.slice(1));st.windBase=st.windDir=10*(1+Math.floor(r()*36));st.windKt=1+Math.floor(r()*10);st.windPh=r()*6.28;}
  const T=api.TYPES[type];
  if(nm===1){st.flapIdx=T.landFlap;st.gearDown=true;st.gearPos=1;}
  api.trimSpawn(st,-api.GS);
  st.easy=true;st.noPF=true;
  const ev=[],DT=1/120;let t=0,td=null,bounce=false,maxLat=0,res=null,lat0=0,log=[];
  const rel=()=>{const rx=st.pos.x-E.x,rz=st.pos.z-E.z;return [rx*dx+rz*dz,rx*(-dz)+rz*dx];};   // along past the threshold, right of the centreline
  let lp=-9;
  while(t<420){
    // one phone frame: the controls are read (hands off: no stick, no brake), then two physics substeps
    st.ail=0;st.elev=0;st.rud=0;st.steer=0;st.brake=false;
    for(let i=0;i<2;i++){api.autopilot(st,DT,ev);api.step(st,DT,ev);t+=DT;if(st.crashed)break;}
    while(ev.length){const q=ev.shift();
      if(q.type==='touchdown'&&!td){const r=rel();td={a:r[0],lat:r[1],fpm:q.fpm,paved:q.paved,kt:q.ias*1.943844,t:t};}
      else if(q.type==='liftoff'&&td)bounce=true;
      if(VERB&&q.type==='ap')log.push(t.toFixed(1)+' '+q.msg);}
    if(VERB&&t-lp>=(st.agl<25&&!st.onGround?0.5:2)){lp=t;const e=new THREE.Euler().setFromQuaternion(st.quat,'YXZ'),r=rel();
      log.push(`t${t.toFixed(0)} a${r[0].toFixed(0)} lat${r[1].toFixed(1)} agl${(st.agl*3.28).toFixed(0)}ft kt${(st.ias*1.944).toFixed(0)} p${(e.x*57.3).toFixed(1)} b${(e.z*57.3).toFixed(1)} vs${(st.vel.y*196.85).toFixed(0)} thr${st.throttle.toFixed(2)} fl${st.flapIdx} g${st.onGround?1:0} hd${(wrap(-e.y-E.h)*57.3).toFixed(1)} tk${(wrap(Math.atan2(st.vel.x,-st.vel.z)-E.h)*57.3).toFixed(1)} be${(st.beta*57.3).toFixed(1)}`);}
    if(st.crashed){res='CRASH '+st.crashReason;break;}
    if(td){const r=rel();maxLat=Math.max(maxLat,Math.abs(r[1]));
      if(r[0]>E.len-E.thr){res='overrun';break;}
      if(st.onGround&&st.vel.length()<2)break;}
  }
  Math.random=RND0;
  const fails=[];
  if(res)fails.push(res);
  else if(!td)fails.push('no touchdown');
  else{
    if(!td.paved)fails.push('off pavement');
    if(td.a<0)fails.push('short '+td.a.toFixed(0)+'m');
    if(td.a>914)fails.push('long '+td.a.toFixed(0)+'m');
    if(td.fpm>=300)fails.push(td.fpm+'fpm');
    if(bounce)fails.push('bounce');
    if(Math.abs(td.lat)>3)fails.push('td lat '+td.lat.toFixed(1)+'m');
    if(maxLat>4)fails.push('roll lat '+maxLat.toFixed(1)+'m');
    if(st.vel.length()>=2)fails.push('still rolling');
  }
  return {ok:!fails.length,fails,td,maxLat,log};
}
module.exports={fly,api};
if(require.main===module){
  const cnt={},M={},W={};let bad=0,n=0;const t0=Date.now();
  for(const ty of TYPES){cnt[ty]=0;M[ty]={};W[ty]={a0:1e9,a1:-1e9,fpm:0,lat:0,roll:0};
    for(const [ei,E] of ENDS.entries())for(const nm of FINALS)for(const w of WINDS){
      const r=fly(ty,E,nm,w,E.idx);n++;const key=E.apt+' '+E.num;M[ty][key]=(M[ty][key]||0)+(r.ok?0:1);
      if(r.td){const q=W[ty];q.a0=Math.min(q.a0,r.td.a);q.a1=Math.max(q.a1,r.td.a);q.fpm=Math.max(q.fpm,r.td.fpm);q.lat=Math.max(q.lat,Math.abs(r.td.lat));q.roll=Math.max(q.roll,r.maxLat);}
      const tag=`${ty.padEnd(6)} ${E.apt} ${E.num.padEnd(3)} ${nm}nm ${w.padEnd(4)}`;
      const info=r.td?`td ${r.td.a.toFixed(0)}m ${r.td.fpm}fpm lat ${r.td.lat.toFixed(1)} roll ${r.maxLat.toFixed(1)} ${r.td.kt.toFixed(0)}kt`:'';
      if(!r.ok){bad++;cnt[ty]++;}
      if(!r.ok||VERB)console.log((r.ok?'ok   ':'FAIL ')+tag+' '+info+(r.ok?'':'  <- '+r.fails.join(', ')));
      if(VERB)console.log(r.log.join('\n'));
    }}
  const keys=ENDS.map(E=>E.apt+' '+E.num);
  console.log('failures, aircraft x runway end ('+FINALS.length*WINDS.length+' runs per cell: finals '+FINALS.join('/')+' nm x winds '+WINDS.length+')');
  console.log('        '+keys.map(k=>k.padStart(9)).join(''));
  for(const ty of TYPES)console.log(ty.padEnd(8)+keys.map(k=>String(M[ty][k]).padStart(9)).join('')+
    `   td ${W[ty].a0.toFixed(0)}..${W[ty].a1.toFixed(0)} m, worst ${W[ty].fpm} fpm, lat ${W[ty].lat.toFixed(1)} m, rollout ${W[ty].roll.toFixed(1)} m`);
  console.log('failures per aircraft:',JSON.stringify(cnt),`${bad}/${n} failed, ${((Date.now()-t0)/1000).toFixed(0)} s`);
  process.exit(bad?1:0);
}
