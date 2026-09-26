const {api}=require('./test.js');const THREE=require('three');
let fails=0,n=0;
for(const ty of ['reaper','cessna','f16']){
 for(let k=0;k<12;k++){
  api.setType(ty);const st=api.createState('final');const AC=api.AC;
  const ang=k/12*Math.PI*2, r=4000+ (k%3)*3000; const hd=(k*97)%360*Math.PI/180;
  const V=AC.vcruise*0.8; st.pos.set(Math.cos(ang)*r, 300+(k%4)*150, Math.sin(ang)*r);
  st.vel.set(Math.sin(hd)*V,0,-Math.cos(hd)*V);st.quat.setFromEuler(new THREE.Euler(0.05,-hd,0,'YXZ'));st.throttle=st.power=0.5;st.flapIdx=0;st.gearDown=false;st.gearPos=AC.retract?0:1;
  api.apEngage(st,'land');const ev=[];let t=0,td=null,ga=0;
  while(t<1200){api.autopilot(st,1/120,ev);api.step(st,1/120,ev);t+=1/120;
   while(ev.length){const e=ev.shift();if(e.type==='touchdown')td=e.fpm;if(e.msg&&/going/.test(e.msg))ga++;}
   if(st.crashed||!st.ap)break;}
  n++;const ok=!st.crashed&&!st.ap;if(!ok)fails++;
  console.log(ty,k,ok?'OK':'FAIL',st.crashed?st.crashReason:'', 'td',td,'ga',ga,'t',t.toFixed(0));
 }}
console.log('fails',fails,'/',n);
