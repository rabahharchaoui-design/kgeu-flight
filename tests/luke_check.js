// Luke AFB siting: is the base where it is in the real world, relative to KGEU?
const THREE=require('three');global.THREE=THREE;
const fs=require('fs');const src=fs.readFileSync(__dirname+'/../index.html','utf8');
const phys=src.split('// PHYSICS-START')[1].split('// PHYSICS-END')[0];
const a=new Function('THREE',phys+'\nreturn {LUKE,LUKE_RWY,lukeUV,toU,toV,wX,wZ,RWY_LEN,isPaved,MAGVAR};')(THREE);

// FAA airport data
const KGEU={lat:33.52683,lon:-112.29517};   // Glendale Municipal ARP
const KLUF={lat:33.53472,lon:-112.38306};   // Luke AFB ARP
const MPD_LAT=110.95, MPD_LON=111.32*Math.cos(KGEU.lat*Math.PI/180);   // km per degree
const north=(KLUF.lat-KGEU.lat)*MPD_LAT*1000;
const east =(KLUF.lon-KGEU.lon)*MPD_LON*1000;
// KGEU ARP sits at the runway midpoint: u = RWY_LEN/2, v = 0
const arpX=a.wX(a.RWY_LEN/2,0), arpZ=a.wZ(a.RWY_LEN/2,0);
const wantX=arpX+east, wantZ=arpZ-north;       // world is +X east, -Z north
const dx=a.LUKE.x-wantX, dz=a.LUKE.z-wantZ, err=Math.hypot(dx,dz);
console.log('KGEU ARP in world       ', arpX.toFixed(0), arpZ.toFixed(0));
console.log('Luke should be at       ', wantX.toFixed(0), wantZ.toFixed(0));
console.log('Luke is at              ', a.LUKE.x, a.LUKE.z);
console.log('error                   ', err.toFixed(0), 'm   (', dx.toFixed(0), ',', dz.toFixed(0), ')');
console.log('distance KGEU to Luke   ', (Math.hypot(east,north)/1852).toFixed(2), 'nm   bearing',
  ((Math.atan2(east,north)*180/Math.PI+360)%360).toFixed(0));
const hTrue=30.6+a.MAGVAR;   // runway 03 magnetic 030.6, plus east variation
console.log('runway 03 true heading  ', hTrue.toFixed(1), 'deg    code has', (a.LUKE.h*180/Math.PI).toFixed(1));
// each runway, measured through isPaved the way the game sees it
const PUB={'03L':9910,'03R':10012};
let bad=0;
for(const r of a.LUKE_RWY){
  let minU=1e9,maxU=-1e9;
  for(let u=-2600;u<=2600;u+=2){
    const x=a.LUKE.x+Math.sin(a.LUKE.h)*u+Math.cos(a.LUKE.h)*r.v, z=a.LUKE.z-Math.cos(a.LUKE.h)*u+Math.sin(a.LUKE.h)*r.v;
    if(a.isPaved(x,z)){minU=Math.min(minU,u);maxU=Math.max(maxU,u);}}
  const ft=(maxU-minU)*3.28084, err=Math.abs(ft-PUB[r.lo]);
  if(err>60)bad++;
  console.log(`runway ${r.lo}/${r.hi}`.padEnd(24), ft.toFixed(0).padStart(6),'ft   published',PUB[r.lo],'  error',err.toFixed(0),'ft');
}
const sep=Math.abs(a.LUKE_RWY[1].v-a.LUKE_RWY[0].v);
console.log('runway separation       ', sep.toFixed(0),'m =',(sep*3.28084).toFixed(0),'ft   published about 1,000 ft');
if(err>60)bad++;
console.log(bad?('FAIL '+bad+' runway(s) off by more than 60 ft'):'luke OK');
process.exit(bad?1:0);
