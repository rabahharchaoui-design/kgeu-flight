// Unit test for the Dubins planner inside the physics block.
const THREE=require('three');global.THREE=THREE;
const fs=require('fs');const src=fs.readFileSync(__dirname+'/../index.html','utf8');
const phys=src.split('// PHYSICS-START')[1].split('// PHYSICS-END')[0];
const api=new Function('THREE',phys+'\nreturn {dubinsPlan,dubinsAt};')(THREE);
let bad=0,shown=0;
let s=99;const rnd=()=>{s=(Math.imul(s,1664525)+1013904223)>>>0;return s/4294967296;};
for(let i=0;i<500;i++){
  const x0=(rnd()-0.5)*8000,y0=(rnd()-0.5)*8000,t0=rnd()*7-3.5;
  const x1=(rnd()-0.5)*8000,y1=(rnd()-0.5)*8000,t1=rnd()*7-3.5;
  const R=200+rnd()*2000;
  const pl=api.dubinsPlan(x0,y0,t0,x1,y1,t1,R);
  if(!pl){bad++;console.log('no plan',i);continue;}
  const e=api.dubinsAt(pl,pl.len,[0,0,0]),st=api.dubinsAt(pl,0,[0,0,0]);
  const perr=Math.hypot(e[0]-x1,e[1]-y1);
  const herr=Math.abs(Math.atan2(Math.sin(e[2]-t1),Math.cos(e[2]-t1)));
  const serr=Math.hypot(st[0]-x0,st[1]-y0);
  if(perr>1||herr>0.01||serr>1e-6){bad++;if(shown++<6)console.log('FAIL',i,'w',pl.w,'len',pl.len.toFixed(0),'perr',perr.toFixed(2),'herr',herr.toFixed(4),'serr',serr.toExponential(2));}
}
console.log(bad?('dubins FAIL '+bad+'/500'):'dubins OK 500/500');
process.exit(bad?1:0);
