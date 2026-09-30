const {api}=require('./test.js');const THREE=require('three');
// the wind (direction, strength, gusts) is drawn from a fixed seed, so every run flies the same air
const SEED={cessna:61,reaper:62,f16:63};
for(const ty of ['cessna','reaper','f16']){
 api.setType(ty);const AC=api.AC;api.windSeed(SEED[ty]);
 // hands-off landing from final
 let st=api.createState('final');st.easy=true;let ev=[],t=0,res='none';
 while(t<200){st.ail=0;st.elev=0;api.autopilot(st,1/120,ev);api.step(st,1/120,ev);t+=1/120;
  while(ev.length){const q=ev.shift();if(q.type==='touchdown')res='TD '+q.fpm+' paved '+q.paved+' u '+api.toU(q.x,q.z).toFixed(0);}
  if(st.crashed){res='CRASH '+st.crashReason;break;} if(st.onGround&&st.vel.length()<1)break; if(st.onGround)st.throttle=0,st.brake=true;}
 console.log(ty,'handsoff final:',res);
 // manual takeoff with easy
 api.windSeed(SEED[ty]+100);st=api.createState('runway');st.easy=true;st.noPF=true;ev=[];t=0;let lo=null;
 while(t<80){st.throttle=1;st.ail=0;st.elev=(st.ias>=AC.vr||!st.onGround)&&t<lo+4||(st.ias>=AC.vr&&lo===null)?0.8:0;
  api.autopilot(st,1/120,ev);api.step(st,1/120,ev);t+=1/120;
  while(ev.length){const q=ev.shift();if(q.type==='liftoff'&&lo===null)lo=t;if(q.type==='ap')console.log('  ',t.toFixed(1),q.msg);}
  if(st.crashed){console.log('CRASH',st.crashReason);break;}}
 const e=new THREE.Euler().setFromQuaternion(st.quat,'YXZ');
 console.log(ty,'takeoff: liftoff',lo&&lo.toFixed(1),'alt',(st.pos.y).toFixed(0),'ias',(st.ias*1.944).toFixed(0),'vs',(st.vel.y*196.85).toFixed(0),'bank',(e.z*57.3).toFixed(1),'stalled',st.stalled);
}
