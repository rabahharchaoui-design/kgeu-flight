const THREE=require('three');global.THREE=THREE;
const fs=require('fs');const src=fs.readFileSync(__dirname+'/../index.html','utf8');
const phys=src.split('// PHYSICS-START')[1].split('// PHYSICS-END')[0];
const api=new Function('THREE',phys+'\nreturn {createState,setType,toU,toV,wX,wZ,THR01,dubinsPlan,get AC(){return AC}};')(THREE);
const base=JSON.parse(fs.readFileSync(__dirname+'/bench_baseline.json'));
// Hard lower bound: shortest feasible (Dubins) route at the approach-speed turn radius,
// flown at the type cruise TAS, plus the final at approach speed, plus a rollout.
for(const ty of ['cessna','reaper','f16']){
  api.setType(ty);const AC=api.AC;
  const TD_U=api.THR01+300,fafU=TD_U-AC.fafD,fx=api.wX(fafU,0),fz=api.wZ(fafU,0);
  const RH=26*Math.PI/180;
  const vT=Math.max(AC.vapp*1.15,AC.vcruise*0.55)/0.93;
  const R=vT*vT/(9.81*Math.tan(AC.maxBank));
  let tot=0,bt=0;
  for(let k=0;k<12;k++){
    const ang=k/12*Math.PI*2,r=4000+(k%3)*3000,hd=(k*97)%360*Math.PI/180;
    const px=Math.cos(ang)*r,pz=Math.sin(ang)*r;
    // most generous bound: free choice of a constant routing speed between approach and
    // cruise, with the turn radius that speed implies, and no deceleration cost at all
    let best=1e9;
    for(let i=0;i<=40;i++){
      const vI=AC.vapp+(AC.vcruise-AC.vapp)*i/40, vTas=vI/0.93;
      const Rv=vTas*vTas/(9.81*Math.tan(AC.maxBank));
      const p2=api.dubinsPlan(px,-pz,Math.PI/2-hd,fx,-fz,Math.PI/2-RH,Rv);
      if(!p2)continue;
      best=Math.min(best,p2.len/vTas);
    }
    const tRoute=best;
    const tFinal=(AC.fafD+300)/(AC.vapp/0.93);
    const t=tRoute+tFinal+18;                          // 18 s rollout
    tot+=t;bt+=base.rand[ty].rows[k].t;
  }
  const lb=tot/12, b=bt/12;
  console.log(`${ty.padEnd(7)} baseline avg ${b.toFixed(1)}s   hard lower bound ${lb.toFixed(1)}s  (${((lb-b)/b*100).toFixed(0)}% vs baseline)   40% target ${(b*0.6).toFixed(1)}s`);
}
