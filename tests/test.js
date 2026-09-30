const THREE=require('three');global.THREE=THREE;
const fs=require('fs');const src=fs.readFileSync(process.env.F||__dirname+'/../index.html','utf8');
const phys=src.split('// PHYSICS-START')[1].split('// PHYSICS-END')[0];
const api=new Function('THREE',phys+'\nreturn {createState,step,setType,autopilot,apEngage,windSeed,toU,toV,wX,wZ,THR01,RWY_LEN,TYPES,M2FT:3.28084,get AC(){return AC}};')(THREE);
function run(type,mode,apMode,T,opts){
  api.setType(type);const st=api.createState(mode);const ev=[];const DT=1/120;
  if(opts&&opts.pre)opts.pre(st);
  api.apEngage(st,apMode);let t=0,log=[],lastPrint=-99,maxAlt=0;
  while(t<T){api.autopilot(st,DT,ev);api.step(st,DT,ev);t+=DT;
    maxAlt=Math.max(maxAlt,st.pos.y);
    while(ev.length){const e=ev.shift();log.push(t.toFixed(1)+' '+JSON.stringify(e));}
    if(st.crashed){log.push('CRASH '+st.crashReason+' t='+t.toFixed(1));break;}
    if(opts&&opts.every&&t-lastPrint>=opts.every){lastPrint=t;const e=new THREE.Euler().setFromQuaternion(st.quat,'YXZ');
      log.push(`t${t.toFixed(0)} u${api.toU(st.pos.x,st.pos.z).toFixed(0)} v${api.toV(st.pos.x,st.pos.z).toFixed(0)} y${(st.pos.y-1.5).toFixed(0)} ias${(st.ias*1.944).toFixed(0)} p${(e.x*57.3).toFixed(1)} b${(-e.z*57.3).toFixed(1)} a${(st.alpha*57.3).toFixed(1)} thr${st.throttle.toFixed(2)} vs${(st.vel.y*196.85).toFixed(0)} ${st.ap?st.ap.mode+'/'+st.ap.phase:'off'}`);}
    if(!st.ap&&apMode==='land')break;
  }
  return {st,log,t,maxAlt};
}
module.exports={api,run};
if(require.main===module){
 for(const ty of ['reaper','cessna','f16']){
  console.log('==== '+ty+' TAKEOFF');
  let r=run(ty,'runway','to',150,{every:10});console.log(r.log.join('\n'));
  console.log('==== '+ty+' LAND from hold (continue)');
  const st0=r.st;
  api.setType(ty);api.apEngage(st0,'land');let ev=[],t=0,lp=-99;const DT=1/120;
  while(t<900){api.autopilot(st0,DT,ev);api.step(st0,DT,ev);t+=DT;
    while(ev.length)console.log(t.toFixed(1),JSON.stringify(ev.shift()));
    if(st0.crashed){console.log('CRASH',st0.crashReason);break;}
    if(t-lp>=20){lp=t;const e=new THREE.Euler().setFromQuaternion(st0.quat,'YXZ');console.log(`t${t.toFixed(0)} u${api.toU(st0.pos.x,st0.pos.z).toFixed(0)} v${api.toV(st0.pos.x,st0.pos.z).toFixed(0)} y${(st0.pos.y-1.5).toFixed(0)} ias${(st0.ias*1.944).toFixed(0)} p${(e.x*57.3).toFixed(1)} b${(-e.z*57.3).toFixed(1)} a${(st0.alpha*57.3).toFixed(1)} thr${st0.throttle.toFixed(2)} vs${(st0.vel.y*196.85).toFixed(0)} ${st0.ap?st0.ap.mode+'/'+st0.ap.phase:'off'}`);}
    if(!st0.ap)break;}
  console.log('==== '+ty+' LAND from final');
  r=run(ty,'final','land',400,{every:10});console.log(r.log.join('\n'));
 }
}
