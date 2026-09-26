// Autoland timing benchmark. node tests/bench.js [label]
// Deterministic: Math.random is seeded so before/after runs are comparable.
const THREE=require('three');global.THREE=THREE;
const fs=require('fs');const src=fs.readFileSync(process.env.F||__dirname+'/../index.html','utf8');
const phys=src.split('// PHYSICS-START')[1].split('// PHYSICS-END')[0];
const api=new Function('THREE',phys+'\nreturn {createState,step,setType,autopilot,apEngage,toU,toV,wX,wZ,THR01,RWY_LEN,TYPES,isPaved,get AC(){return AC}};')(THREE);
let _s=12345;function seed(n){_s=n>>>0;}
Math.random=function(){_s=(Math.imul(_s,1664525)+1013904223)>>>0;return _s/4294967296;};
const DT=1/120;
function flyLand(st,limit){ // returns {t, fpm, paved, crash, ga, tNav, tLoc, tRoll, dist}
  const ev=[];let t=0,fpm=null,paved=null,ga=0,tNav=0,tLoc=0,tRoll=0,dist=0;
  api.apEngage(st,'land');
  while(t<(limit||1800)){
    api.autopilot(st,DT,ev);api.step(st,DT,ev);t+=DT;
    const ph=st.ap?st.ap.phase:'-';
    if(st.onGround)tRoll+=DT;else if(ph==='loc')tLoc+=DT;else tNav+=DT;
    dist+=Math.hypot(st.vel.x,st.vel.z)*DT;
    while(ev.length){const e=ev.shift();if(e.type==='touchdown'){fpm=e.fpm;paved=e.paved;}if(e.msg&&/going around/.test(e.msg))ga++;}
    const r={t:t,fpm:fpm,paved:paved,ga:ga,tNav:tNav,tLoc:tLoc,tRoll:tRoll,dist:dist};
    if(st.crashed){r.crash=st.crashReason;return r;}
    if(!st.ap){r.crash=null;return r;}
  }
  return{t:t,fpm:fpm,paved:paved,crash:'TIMEOUT',ga:ga,tNav:tNav,tLoc:tLoc,tRoll:tRoll,dist:dist};
}
function holdState(ty){ // fly the auto takeoff to the hold, return the state
  api.setType(ty);const st=api.createState('runway');const ev=[];let t=0;
  api.apEngage(st,'to');
  while(t<300){api.autopilot(st,DT,ev);api.step(st,DT,ev);t+=DT;ev.length=0;
    if(st.crashed)throw new Error(ty+' takeoff crashed: '+st.crashReason);
    if(st.ap&&st.ap.mode==='hold')return{st:st,t:t};}
  throw new Error(ty+' never reached hold');
}
function randStart(ty,k){
  api.setType(ty);const st=api.createState('final');const AC=api.AC;
  const ang=k/12*Math.PI*2,r=4000+(k%3)*3000,hd=(k*97)%360*Math.PI/180;
  const V=AC.vcruise*0.8;st.pos.set(Math.cos(ang)*r,300+(k%4)*150,Math.sin(ang)*r);
  st.vel.set(Math.sin(hd)*V,0,-Math.cos(hd)*V);st.quat.setFromEuler(new THREE.Euler(0.05,-hd,0,'YXZ'));
  st.throttle=st.power=0.5;st.flapIdx=0;st.gearDown=false;st.gearPos=AC.retract?0:1;
  return st;
}
const TYS=['cessna','reaper','f16'];
const out={label:process.argv[2]||'run',hold:{},rand:{}};
console.log('=== autoland benchmark:',out.label,'===');
for(const ty of TYS){
  seed(7);
  const h=holdState(ty);
  const r=flyLand(h.st);
  out.hold[ty]={t:r.t,fpm:r.fpm,paved:r.paved,crash:r.crash,ga:r.ga};
  console.log(`hold  ${ty.padEnd(7)} t=${r.t.toFixed(1)}s fpm=${r.fpm} paved=${r.paved} ga=${r.ga} ${r.crash||''}`);
}
for(const ty of TYS){
  const rows=[];let fails=0;
  for(let k=0;k<12;k++){
    seed(1000+k);
    const r=flyLand(randStart(ty,k));
    const ok=!r.crash&&r.paved===true;if(!ok)fails++;
    rows.push(r);
    console.log(`rand  ${ty.padEnd(7)} k=${String(k).padStart(2)} t=${r.t.toFixed(0).padStart(4)}s nav=${r.tNav.toFixed(0).padStart(4)} loc=${r.tLoc.toFixed(0).padStart(3)} roll=${r.tRoll.toFixed(0).padStart(3)} km=${(r.dist/1000).toFixed(1).padStart(5)} fpm=${String(r.fpm).padStart(4)} ga=${r.ga} ${ok?'OK':'FAIL '+(r.crash||'unpaved')}`);
  }
  const ts=rows.map(r=>r.t);
  out.rand[ty]={avg:ts.reduce((a,b)=>a+b,0)/ts.length,max:Math.max(...ts),min:Math.min(...ts),fails:fails,
    maxFpm:Math.max(...rows.map(r=>r.fpm===null?0:r.fpm)),rows:rows.map(r=>({t:r.t,fpm:r.fpm,paved:r.paved,crash:r.crash,tNav:r.tNav,tLoc:r.tLoc,tRoll:r.tRoll,dist:r.dist}))};
}
console.log('\n--- summary ---');
console.log('type     hold_t   rand_avg  rand_min rand_max  fails  maxfpm');
let tf=0;
for(const ty of TYS){const R=out.rand[ty];tf+=R.fails;
  console.log(`${ty.padEnd(8)} ${out.hold[ty].t.toFixed(1).padStart(6)}  ${R.avg.toFixed(1).padStart(8)}  ${R.min.toFixed(1).padStart(7)} ${R.max.toFixed(1).padStart(8)}  ${String(R.fails).padStart(5)}  ${String(R.maxFpm).padStart(6)}`);}
console.log('total fails',tf,'/ 36');
fs.writeFileSync(__dirname+'/bench_'+out.label+'.json',JSON.stringify(out,null,1));
